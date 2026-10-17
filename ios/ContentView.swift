// Lotto Generator для iPhone — оболочка вокруг веб-версии.
//
// Как работает:
//  * открывает https://simafon1-cyber.github.io/lotto-generator/ — там всегда
//    свежая версия программы и тиражи (обновляются каждые 3 часа сами);
//  * если интернета нет — открывает копию, вложенную в приложение (папка web);
//  * ссылки на сайты лотерей открывает в Safari;
//  * показывает окна alert/confirm/prompt, без которых кнопки «Удалить»,
//    «Записать выигрыш» и предупреждения о лимите не работали бы; кнопки
//    этих окон — на языке, выбранном в программе (страница сообщает его).
//
// Готовый проект с этим файлом собирается на GitHub (ios/make_project.sh).
// Если создаёте проект в Xcode вручную — вставьте файл ЦЕЛИКОМ вместо
// ContentView.swift.

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
        let config = WKWebViewConfiguration()
        config.userContentController.add(context.coordinator, name: "lang")
        let web = WKWebView(frame: .zero, configuration: config)
        web.navigationDelegate = context.coordinator
        web.uiDelegate = context.coordinator
        web.allowsBackForwardNavigationGestures = false
        web.load(URLRequest(url: siteURL, cachePolicy: .reloadIgnoringLocalCacheData,
                            timeoutInterval: 15))
        return web
    }

    func updateUIView(_ uiView: WKWebView, context: Context) {}

    final class Coordinator: NSObject, WKNavigationDelegate, WKUIDelegate, WKScriptMessageHandler {
        private var triedOffline = false
        // Язык кнопок в окнах: до первого сообщения от страницы — язык телефона.
        private var lang = String((Locale.preferredLanguages.first ?? "en").prefix(2))

        // Страница сообщает выбранный язык: window.webkit.messageHandlers.lang.postMessage("fr")
        func userContentController(_ controller: WKUserContentController,
                                   didReceive message: WKScriptMessage) {
            if let code = message.body as? String { lang = code }
        }

        private func word(_ key: String) -> String {
            let words: [String: [String: String]] = [
                "cancel": ["ru": "Отмена", "en": "Cancel", "fr": "Annuler"],
                "yes": ["ru": "Да", "en": "Yes", "fr": "Oui"],
            ]
            return words[key]?[lang] ?? words[key]?["en"] ?? key
        }

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
            a.addAction(UIAlertAction(title: word("cancel"), style: .cancel) { _ in completionHandler(false) })
            a.addAction(UIAlertAction(title: word("yes"), style: .default) { _ in completionHandler(true) })
            present(a) { completionHandler(false) }
        }

        // prompt(...)
        func webView(_ webView: WKWebView, runJavaScriptTextInputPanelWithPrompt prompt: String,
                     defaultText: String?, initiatedByFrame frame: WKFrameInfo,
                     completionHandler: @escaping (String?) -> Void) {
            let a = UIAlertController(title: nil, message: prompt, preferredStyle: .alert)
            a.addTextField { $0.text = defaultText; $0.keyboardType = .decimalPad }
            a.addAction(UIAlertAction(title: word("cancel"), style: .cancel) { _ in completionHandler(nil) })
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
