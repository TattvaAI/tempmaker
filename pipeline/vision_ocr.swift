import Foundation
import Vision
import AppKit

struct BoundingBoxResult: Codable {
    let text: String
    let confidence: Float
    let x: Double
    let y: Double
    let w: Double
    let h: Double
}

struct ImageOcrResult: Codable {
    let image: String
    let width: Int
    let height: Int
    let boxes: [BoundingBoxResult]
}

func processImage(path: String) -> ImageOcrResult? {
    guard let image = NSImage(contentsOfFile: path) else {
        return nil
    }
    var rect = CGRect(origin: .zero, size: image.size)
    guard let cgImage = image.cgImage(forProposedRect: &rect, context: nil, hints: nil) else {
        return nil
    }
    
    let width = cgImage.width
    let height = cgImage.height
    var boxes: [BoundingBoxResult] = []
    
    let requestHandler = VNImageRequestHandler(cgImage: cgImage, options: [:])
    let request = VNRecognizeTextRequest { request, error in
        guard let observations = request.results as? [VNRecognizedTextObservation] else { return }
        for obs in observations {
            guard let candidate = obs.topCandidates(1).first else { continue }
            let box = obs.boundingBox
            // Vision has origin at bottom-left; convert y to top-left
            let normX = Double(box.origin.x)
            let normY = Double(1.0 - box.origin.y - box.size.height)
            let normW = Double(box.size.width)
            let normH = Double(box.size.height)
            
            boxes.append(BoundingBoxResult(
                text: candidate.string,
                confidence: candidate.confidence,
                x: normX,
                y: normY,
                w: normW,
                h: normH
            ))
        }
    }
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = true
    
    try? requestHandler.perform([request])
    
    // Sort boxes vertically top to bottom
    boxes.sort { $0.y < $1.y }
    
    return ImageOcrResult(image: path, width: width, height: height, boxes: boxes)
}

let args = CommandLine.arguments
if args.count < 2 {
    fputs("Usage: vision_ocr <image_path_1> [image_path_2 ...]\n", stderr)
    exit(1)
}

var allResults: [ImageOcrResult] = []
for i in 1..<args.count {
    let path = args[i]
    if let result = processImage(path: path) {
        allResults.append(result)
    }
}

let encoder = JSONEncoder()
encoder.outputFormatting = .prettyPrinted
if let jsonData = try? encoder.encode(allResults) {
    if let jsonString = String(data: jsonData, encoding: .utf8) {
        print(jsonString)
    }
}
