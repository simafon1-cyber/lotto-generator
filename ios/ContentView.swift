// Lotto Generator для iPhone — оболочка вокруг веб-версии.
//
// Как работает:
//  * открывает https://simafon1-cyber.github.io/lotto-generator/ — там всегда
//    свежая версия программы и тиражи (обновляются каждые 3 часа сами);
//  * если интернета нет — открывает копию, вложенную в приложение (папка web);
//  * ссылки на сайты лотерей открывает в Safari;
//  * показывает окна alert/confirm/prompt, без которых кнопки «Удалить»,
//    «Записать выигрыш» и предупреждения о лимите не работали бы.
//
// Вставьте этот файл ЦЕЛИКОМ вместо ContentView.swift в новом проекте Xcode.

import SwiftUI
import WebKit

let siteURL = URL(string: "https://simafon1-cyber.github.io/lotto-generator/")!

struct ContentView: View {
    var body: some View {
        LottoWebView()
            .ignoresSafeArea(.container, edges: .bottom)
    }
}

struct LottoWebView: UIViewRepresentable {
    func makeCoordinator() -> Coordinator { Coordinator() }

    func makeUIView(context: Context) -> WKWebView {
        let web = WKWebView(frame: .zero, configuration: WKWebViewConfiguration())
        web.navigationDelegate = context.coordinator
        web.uiDelegate = context.coordinator
        web.allowsBackForwardNavigationGestures = false
        web.load(URLRequest(url: siteURL, cachePolicy: .reloadIgnoringLocalCacheData,
                            timeoutInterval: 15))
        return web
    }

    func updateUIView(_ uiView: WKWebView, context: Context) {}

    final class Coordinator: NSObject, WKNavigationDelegate, WKUIDelegate {
        private var triedOffline = false

        // Нет интернета — открыть вложенную копию.
        func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!,
                     withError error: Error) {
            openOffline(webView)
        }

        func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
            openOffline(webView)
        }

        private func openOffline(_ webView: WKWebView) {
            guard !triedOffline,
                  let page = Bundle.main.url(forResource: "index", withExtension: "html",
                                             subdirectory: "web") else { return }
            triedOffline = true
            webView.loadFileURL(page, allowingReadAccessTo: page.deletingLastPathComponent())
        }

        // Чужие сайты (лотерея) — в Safari, своё — внутри приложения.
        func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction,
                     decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
            if let url = action.request.url, let host = url.host,
               host != siteURL.host, url.scheme == "https" || url.scheme == "http" {
                UIApplication.shared.open(url)
                decisionHandler(.cancel)
                return
            }
            decisionHandler(.allow)
        }

        // window.open(...) — тоже в Safari.
        func webView(_ webView: WKWebView, createWebViewWith configuration: WKWebViewConfiguration,
                     for action: WKNavigationAction, windowFeatures: WKWindowFeatures) -> WKWebView? {
            if let url = action.request.url { UIApplication.shared.open(url) }
            return nil
        }

        // alert(...)
        func webView(_ webView: WKWebView, runJavaScriptAlertPanelWithMessage message: String,
                     initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping () -> Void) {
            let a = UIAlertController(title: nil, message: message, preferredStyle: .alert)
            a.addAction(UIAlertAction(title: "OK", style: .default) { _ in completionHandler() })
            present(a, or: completionHandler)
        }

        // confirm(...)
        func webView(_ webView: WKWebView, runJavaScriptConfirmPanelWithMessage message: String,
                     initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping (Bool) -> Void) {
            let a = UIAlertController(title: nil, message: message, preferredStyle: .alert)
            a.addAction(UIAlertAction(title: "Отмена", style: .cancel) { _ in completionHandler(false) })
            a.addAction(UIAlertAction(title: "Да", style: .default) { _ in completionHandler(true) })
            present(a) { completionHandler(false) }
        }

        // prompt(...)
        func webView(_ webView: WKWebView, runJavaScriptTextInputPanelWithPrompt prompt: String,
                     defaultText: String?, initiatedByFrame frame: WKFrameInfo,
                     completionHandler: @escaping (String?) -> Void) {
            let a = UIAlertController(title: nil, message: prompt, preferredStyle: .alert)
            a.addTextField { $0.text = defaultText; $0.keyboardType = .decimalPad }
            a.addAction(UIAlertAction(title: "Отмена", style: .cancel) { _ in completionHandler(nil) })
            a.addAction(UIAlertAction(title: "OK", style: .default) { _ in
                completionHandler(a.textFields?.first?.text)
            })
            present(a) { completionHandler(nil) }
        }

        private func present(_ alert: UIAlertController, or fallback: @escaping () -> Void) {
            let root = UIApplication.shared.connectedScenes
                .compactMap { ($0 as? UIWindowScene)?.keyWindow?.rootViewController }
                .first
            var top = root
            while let next = top?.presentedViewController { top = next }
            if let top { top.present(alert, animated: true) } else { fallback() }
        }
    }
}
