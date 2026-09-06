import Cocoa

guard CommandLine.arguments.count >= 6 else {
    print("Usage: render_text <text> <font_name> <size> <hex_or_r,g,b> <out_png> [stroke_width] [stroke_hex]")
    exit(1)
}

let text = CommandLine.arguments[1]
let fontName = CommandLine.arguments[2]
let fontSize = CGFloat(Double(CommandLine.arguments[3]) ?? 40.0)
let colorStr = CommandLine.arguments[4]
let outPath = CommandLine.arguments[5]

func parseColor(_ str: String) -> NSColor {
    let parts = str.split(separator: ",").compactMap { Double($0) }
    if parts.count >= 3 {
        let a = parts.count >= 4 ? parts[3] / 255.0 : 1.0
        return NSColor(red: parts[0]/255.0, green: parts[1]/255.0, blue: parts[2]/255.0, alpha: a)
    }
    return .black
}

let font = NSFont(name: fontName, size: fontSize) ?? NSFont.systemFont(ofSize: fontSize)
var attr: [NSAttributedString.Key: Any] = [
    .font: font,
    .foregroundColor: parseColor(colorStr)
]

let attrString = NSAttributedString(string: text, attributes: attr)
let size = attrString.size()
let width = max(1, Int(ceil(size.width)))
let height = max(1, Int(ceil(size.height)))

let image = NSImage(size: NSSize(width: width, height: height))
image.lockFocus()
attrString.draw(at: .zero)
image.unlockFocus()

if let tiff = image.tiffRepresentation,
   let rep = NSBitmapImageRep(data: tiff),
   let png = rep.representation(using: .png, properties: [:]) {
    try? png.write(to: URL(fileURLWithPath: outPath))
}
