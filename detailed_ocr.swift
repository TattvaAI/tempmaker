import Foundation
import Vision
import AppKit

let fileManager = FileManager.default
let files = (try? fileManager.contentsOfDirectory(atPath: "frames"))?.filter { $0.hasSuffix(".png") }.sorted() ?? []

for file in files {
    let path = "frames/" + file
    guard let image = NSImage(contentsOfFile: path),
          let cgImage = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
        continue
    }
    
    let requestHandler = VNImageRequestHandler(cgImage: cgImage, options: [:])
    let request = VNRecognizeTextRequest { request, error in
        guard let observations = request.results as? [VNRecognizedTextObservation] else { return }
        for obs in observations {
            guard let candidate = obs.topCandidates(1).first else { continue }
            let box = obs.boundingBox
            print(String(format: "%@: [%.2f, %.2f, %.2f, %.2f] \"%@\"", file, box.origin.x, box.origin.y, box.size.width, box.size.height, candidate.string))
        }
    }
    request.recognitionLevel = .accurate
    try? requestHandler.perform([request])
}
