import Foundation
import Vision
import AppKit

for i in 1...52 {
    let filename = String(format: "frames/frame_%03d.png", i)
    guard let image = NSImage(contentsOfFile: filename),
          let cgImage = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
        continue
    }
    
    let requestHandler = VNImageRequestHandler(cgImage: cgImage, options: [:])
    let request = VNRecognizeTextRequest { request, error in
        guard let observations = request.results as? [VNRecognizedTextObservation] else { return }
        let strings = observations.compactMap { $0.topCandidates(1).first?.string }
        if !strings.isEmpty {
            print("Frame \(i): \(strings.joined(separator: " | "))")
        }
    }
    request.recognitionLevel = .accurate
    try? requestHandler.perform([request])
}
