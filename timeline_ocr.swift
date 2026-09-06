import Foundation
import Vision
import AppKit

let fileManager = FileManager.default
let files = (try? fileManager.contentsOfDirectory(atPath: "timeline_frames"))?.filter { $0.hasSuffix(".jpg") }.sorted() ?? []

for file in files {
    let path = "timeline_frames/" + file
    guard let image = NSImage(contentsOfFile: path),
          let cgImage = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
        continue
    }
    
    let requestHandler = VNImageRequestHandler(cgImage: cgImage, options: [:])
    let request = VNRecognizeTextRequest { request, error in
        guard let observations = request.results as? [VNRecognizedTextObservation] else { return }
        let texts = observations.compactMap { $0.topCandidates(1).first?.string }
        if !texts.isEmpty {
            print("\(file): \(texts.joined(separator: " | "))")
        } else {
            print("\(file): [NO TEXT]")
        }
    }
    request.recognitionLevel = .accurate
    try? requestHandler.perform([request])
}
