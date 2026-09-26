// share.swift — the owner shares a screen or a window with the agent, the way a call does: the Mac's own picker
// (ScreenCaptureKit's SCContentSharingPicker) asks which display, window or app; the pick streams at two frames a
// second into <dir>/live.jpg (a JPEG no longer than 1600 px on its long side, replaced atomically), and <dir>/share.json
// says what is shared (kind, title, app, its bounds in screen points, the frame size, since, last). The share ends when
// the owner stops it from the menu bar or the picker, when a file named <dir>/stop appears (share.sh stop), or on SIGTERM;
// share.json then carries "ended" and why. Screen Recording permission belongs to the terminal the agent runs under.
//   share start <dir>
// Built by share.sh (or install.sh) with: xcrun swiftc -O -swift-version 5 -framework ScreenCaptureKit -framework AppKit
import AppKit
import CoreImage
import CoreMedia
import ScreenCaptureKit

let fm = FileManager.default

func now() -> Double { Date().timeIntervalSince1970 }

func writeAtomic(_ data: Data, to url: URL) {
    let tmp = url.appendingPathExtension("tmp")
    do {
        try data.write(to: tmp)
        if rename(tmp.path, url.path) != 0 { try? fm.removeItem(at: tmp) }
    } catch { }
}

@available(macOS 14.0, *)
final class Sharer: NSObject, SCContentSharingPickerObserver, SCStreamDelegate, SCStreamOutput {
    let dir: URL
    let since = now()
    let ctx = CIContext(options: [.cacheIntermediates: false])
    let queue = DispatchQueue(label: "share.frames")
    var stream: SCStream?
    var info: [String: Any] = [:]
    var frames = 0

    init(dir: URL) { self.dir = dir }

    func begin() {
        let picker = SCContentSharingPicker.shared
        var cfg = SCContentSharingPickerConfiguration()
        cfg.allowedPickerModes = [.singleWindow, .singleDisplay, .singleApplication]
        cfg.allowsChangingSelectedContent = true
        picker.defaultConfiguration = cfg
        picker.add(self)
        picker.isActive = true
        picker.present()
        writeInfo(["state": "picking", "since": since, "pid": Int(getpid())])
    }

    // MARK: the picker
    func contentSharingPicker(_ picker: SCContentSharingPicker, didUpdateWith filter: SCContentFilter, for stream: SCStream?) {
        describe(filter)
        if let s = self.stream {
            s.updateContentFilter(filter) { err in if let e = err { self.log("filter: \(e.localizedDescription)") } }
            let conf = self.configuration(for: filter)
            s.updateConfiguration(conf) { _ in }
            return
        }
        let s = SCStream(filter: filter, configuration: configuration(for: filter), delegate: self)
        do { try s.addStreamOutput(self, type: .screen, sampleHandlerQueue: queue) } catch { fail("output: \(error.localizedDescription)"); return }
        s.startCapture { err in if let e = err { self.fail("start: \(e.localizedDescription)") } }
        self.stream = s
    }

    func contentSharingPicker(_ picker: SCContentSharingPicker, didCancelFor stream: SCStream?) {
        finish(self.stream == nil ? "cancelled in the picker" : "stopped from the picker")
    }

    func contentSharingPickerStartDidFailWithError(_ error: Error) { fail("picker: \(error.localizedDescription)") }

    // MARK: the stream
    func configuration(for filter: SCContentFilter) -> SCStreamConfiguration {
        let conf = SCStreamConfiguration()
        let rect = filter.contentRect
        let scale = CGFloat(filter.pointPixelScale)
        var w = max(rect.width * scale, 2), h = max(rect.height * scale, 2)
        let long = max(w, h)
        if long > 1600 { let f = 1600 / long; w *= f; h *= f }
        conf.width = Int(w); conf.height = Int(h)
        conf.minimumFrameInterval = CMTime(value: 1, timescale: 2)      // two frames a second is plenty for a reader that thinks in turns
        conf.pixelFormat = kCVPixelFormatType_32BGRA
        conf.showsCursor = true
        conf.queueDepth = 3
        return conf
    }

    func stream(_ stream: SCStream, didStopWithError error: Error) { finish("the stream stopped: \(error.localizedDescription)") }

    func stream(_ stream: SCStream, didOutputSampleBuffer sb: CMSampleBuffer, of type: SCStreamOutputType) {
        guard type == .screen, sb.isValid, let pb = CMSampleBufferGetImageBuffer(sb) else { return }
        if let atts = CMSampleBufferGetSampleAttachmentsArray(sb, createIfNecessary: false) as? [[String: Any]],
           let st = atts.first?[SCStreamFrameInfo.status.rawValue] as? Int, st != SCFrameStatus.complete.rawValue { return }
        let img = CIImage(cvPixelBuffer: pb)
        guard let data = ctx.jpegRepresentation(of: img, colorSpace: CGColorSpaceCreateDeviceRGB(),
                                                options: [kCGImageDestinationLossyCompressionQuality as CIImageRepresentationOption: 0.6]) else { return }
        writeAtomic(data, to: dir.appendingPathComponent("live.jpg"))
        frames += 1
        info["last"] = now(); info["frames"] = frames
        info["frame"] = ["w": CVPixelBufferGetWidth(pb), "h": CVPixelBufferGetHeight(pb)]
        info["state"] = "live"
        writeInfo(info)
    }

    // MARK: what is shared
    func describe(_ filter: SCContentFilter) {
        let r = filter.contentRect
        var kind = "content"
        switch filter.style {
        case .window: kind = "window"
        case .display: kind = "display"
        case .application: kind = "application"
        default: kind = "content"
        }
        info["kind"] = kind
        info["bounds"] = ["x": r.origin.x, "y": r.origin.y, "w": r.width, "h": r.height]
        info["scale"] = filter.pointPixelScale
        info["since"] = since; info["pid"] = Int(getpid()); info["state"] = info["state"] ?? "starting"
        writeInfo(info)
        // the window's title and app, found by its frame among the shareable windows (the filter does not say)
        SCShareableContent.getExcludingDesktopWindows(false, onScreenWindowsOnly: true) { content, _ in
            guard let content = content else { return }
            if kind == "window" {
                // the window whose frame overlaps the shared rect most (the rect may leave out the shadow or the title bar)
                func overlap(_ f: CGRect) -> CGFloat { let i = f.intersection(r); return i.isNull ? 0 : (i.width * i.height) / max(1, max(f.width * f.height, r.width * r.height)) }
                if let w = content.windows.filter({ $0.isOnScreen && $0.frame.width > 40 && $0.frame.height > 40 }).max(by: { overlap($0.frame) < overlap($1.frame) }), overlap(w.frame) > 0.5 {
                    self.info["title"] = w.title ?? ""; self.info["app"] = w.owningApplication?.applicationName ?? ""
                }
            } else if kind == "display", let d = content.displays.first(where: { $0.frame == r }) {
                self.info["title"] = "display \(d.displayID)"; self.info["app"] = ""
            }
            self.writeInfo(self.info)
        }
    }

    func writeInfo(_ d: [String: Any]) {
        if let data = try? JSONSerialization.data(withJSONObject: d, options: [.sortedKeys]) { writeAtomic(data, to: dir.appendingPathComponent("share.json")) }
    }

    func log(_ s: String) { FileHandle.standardError.write((s + "\n").data(using: .utf8)!) }

    func finish(_ why: String) {
        stream?.stopCapture { _ in }
        var d = info; d["state"] = "ended"; d["ended"] = now(); d["why"] = why
        writeInfo(d)
        try? fm.removeItem(at: dir.appendingPathComponent("live.jpg"))    // the picture of a share that is over is nobody's to keep
        log("share: \(why) after \(frames) frames")
        exit(0)
    }

    func fail(_ why: String) {
        var d = info; d["state"] = "ended"; d["ended"] = now(); d["why"] = why; d["error"] = true
        writeInfo(d); log("share: \(why)"); exit(1)
    }
}

// MARK: main
let args = CommandLine.arguments
guard args.count >= 3, args[1] == "start" else {
    print("share start <dir>   (the picker appears; frames land in <dir>/live.jpg, the description in <dir>/share.json)")
    exit(2)
}
guard #available(macOS 14.0, *) else { print("share needs macOS 14 or later"); exit(2) }
let dir = URL(fileURLWithPath: args[2])
try? fm.createDirectory(at: dir, withIntermediateDirectories: true)
try? fm.removeItem(at: dir.appendingPathComponent("stop"))
let app = NSApplication.shared
app.setActivationPolicy(.accessory)
let sharer = Sharer(dir: dir)
signal(SIGTERM) { _ in exit(0) }
signal(SIGINT) { _ in exit(0) }
Timer.scheduledTimer(withTimeInterval: 0.5, repeats: true) { _ in
    if fm.fileExists(atPath: dir.appendingPathComponent("stop").path) {
        try? fm.removeItem(at: dir.appendingPathComponent("stop"))
        sharer.finish("stopped by the agent")
    }
}
sharer.begin()
app.run()
