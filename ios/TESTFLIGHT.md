# Lotto Generator → TestFlight → знакомым

TestFlight — официальная программа Apple для тестирования. Вы отправляете
приложение в Apple, а знакомые ставят его по ссылке через приложение
TestFlight. Каждая сборка работает **90 дней**; потом выкладывается новая
(те же шаги 3–5, занимает 10 минут).

Понадобится: Mac с Xcode, ваша платная учётная запись разработчика,
примерно 40 минут в первый раз. Плюс ожидание проверки Apple — обычно от
нескольких часов до 2 дней.

---

## Шаг 1. Скачать готовый проект

1. Откройте https://github.com/simafon1-cyber/lotto-generator/releases/tag/lottery-latest
2. Скачайте **LottoGenerator-iPhone-Xcode.zip** и дважды щёлкните по нему —
   появится папка `LottoGenerator`.
3. В ней дважды щёлкните **LottoGenerator.xcodeproj** — откроется Xcode.

Создавать проект, вставлять код и папку `web` вручную **не нужно** — всё
уже внутри.

## Шаг 2. Выбрать свою учётную запись

1. Слева вверху щёлкните синий значок **LottoGenerator**.
2. В середине, в разделе **TARGETS**, — **LottoGenerator**.
3. Вкладка **Signing & Capabilities**:
   * галочка **Automatically manage signing**;
   * **Team** — ваша платная учётная запись.
4. Если ниже красным *«…bundle identifier is not available»* — в поле
   **Bundle Identifier** замените `com.simafon.LottoGenerator` на своё,
   например `com.ВашаФамилия.LottoGenerator` (латиницей). Запомните его —
   понадобится в шаге 3.

Проверка: подключите iPhone, выберите его вверху и нажмите **▶** —
приложение должно открыться на телефоне.

## Шаг 3. Создать карточку приложения в App Store Connect

1. Откройте https://appstoreconnect.apple.com и войдите Apple ID
   разработчика.
2. **Apps** (Приложения) → синий **«+»** → **New App**.
3. Заполните:
   * **Platforms:** iOS;
   * **Name:** название, которое увидят знакомые. Оно должно быть
     уникальным во всём App Store и **без** «Lotto Max» и «6/49» (это чужие
     торговые марки). Например: `Lucky Numbers Helper`. Если занято —
     добавьте слово;
   * **Primary Language:** Russian (или English);
   * **Bundle ID:** выберите из списка тот, что в шаге 2
     (`com.simafon.LottoGenerator`). Если списка нет — сначала сделайте
     проверку ▶ из шага 2: Xcode сам зарегистрирует этот номер;
   * **SKU:** любой текст, например `lottogen1`;
   * **User Access:** Full Access.
4. **Create**.

## Шаг 4. Отправить сборку из Xcode

1. Вверху посередине, где имя устройства, выберите
   **Any iOS Device (arm64)**.
2. Меню **Product → Archive**. Подождите 1–3 минуты.
3. Откроется окно **Organizer** с вашим архивом. Нажмите
   **Distribute App**.
4. Выберите **TestFlight & App Store** (в старых Xcode — **App Store
   Connect** → **Upload**) → **Distribute**. Если спросит про сертификаты —
   оставьте как предлагает и нажимайте **Next**.
5. Появится «Upload Succeeded». Через 10–30 минут придёт письмо от Apple,
   что сборка обработана.

Вопрос о шифровании Apple не задаст — ответ уже записан в проекте
(приложение использует только обычный HTTPS).

> Ошибка *«The bundle version must be higher…»*: эта сборка уже
> отправлялась. Скачайте свежий zip с GitHub или в Xcode: **TARGETS →
> LottoGenerator → General → Build** — увеличьте число на 1 и повторите шаг 4.

## Шаг 5. Открыть тестирование для знакомых

В App Store Connect откройте приложение → вкладка **TestFlight**.

### 5.1. Сведения для проверки (один раз)

Слева **Test Information** (Сведения о тестировании) — заполните и
нажмите **Save**:

| Поле | Что вписать |
|---|---|
| Beta App Description | текст «Описание» ниже |
| Feedback Email | ваш e-mail — туда придут отзывы знакомых |
| Privacy Policy URL | `https://simafon1-cyber.github.io/lotto-generator/privacy.html` |
| Marketing URL | можно оставить пустым |
| Beta App Review Information: First/Last Name, Phone, Email | ваши имя, телефон, e-mail (видит только Apple) |
| Sign-in required | **снять** галочку — входа в программе нет |
| Review Notes | текст «Для проверяющего Apple» ниже |

### 5.2. Группа для знакомых

1. Слева рядом с **External Testing** нажмите **«+»** → название группы,
   например `Друзья` → **Create**.
2. В группе вкладка **Builds** → **«+»** → выберите сборку → **Next**.
3. **What to Test** — текст «Что проверить» ниже → **Submit for Review**.
4. Ждите письма «approved» — обычно от нескольких часов до 1–2 дней.

### 5.3. Ссылка

1. После одобрения в группе `Друзья` нажмите **Enable Public Link**
   (Включить общедоступную ссылку). Можно ограничить число людей.
2. Скопируйте ссылку вида `https://testflight.apple.com/join/…` и
   отправьте знакомым.

## Что делают знакомые

1. Ставят из App Store бесплатное приложение **TestFlight** (от Apple).
2. Открывают вашу ссылку на iPhone → **Accept** → **Install**.
3. Значок появится на экране. Обновления приходят через TestFlight сами.

---

## Тексты для заявки (копировать как есть)

### Описание (Beta App Description)

**Русский:**

> Lotto Generator — помощник для выбора чисел в канадских лотереях Lotto
> Max и Lotto 6/49. Показывает, как часто выпадало каждое число за всю
> историю тиражей, предлагает комбинации, хранит купленные вами билеты и
> сам проверяет их после тиража. Программа не продаёт билеты, не принимает
> ставки и не предсказывает тиражи: каждый тираж случаен. Не связана с
> OLG, BCLC и Loto-Québec. 18+.

**English:**

> Lotto Generator is a helper for choosing numbers for the Canadian Lotto
> Max and Lotto 6/49 lotteries. It shows how often each number has been
> drawn over the full draw history, suggests combinations, keeps the
> tickets you bought and checks them after each draw. It does not sell
> tickets, accept bets or predict draws — every draw is random. Not
> affiliated with OLG, BCLC or Loto-Québec. 18+.

### Что проверить (What to Test)

> Сгенерируйте комбинации, отметьте «купленные», проверьте вкладку «Мои»
> после ближайшего тиража. Смените язык (🌐). Напишите, что неудобно или
> непонятно.

### Для проверяющего Apple (Review Notes) — по-английски

> Lotto Generator is a personal helper for choosing numbers for the
> Canadian Lotto Max and Lotto 6/49 lotteries. It shows how often each
> number has been drawn (public BCLC draw history), generates
> combinations, keeps a list of tickets the user bought elsewhere and
> checks them against new draws. The app does not sell tickets, accept
> bets, involve real-money gaming or claim to predict results; it clearly
> states that every draw is random. No account or login. No personal data
> is collected; tickets are stored only on the device. The full app is
> bundled and works offline; draw results are refreshed from our GitHub
> Pages site. Not affiliated with OLG, BCLC or Loto-Québec.

---

## Если что-то пошло не так

| Что видите | Что сделать |
|---|---|
| Красное *«Signing requires a development team»* | Шаг 2: выберите Team |
| В **New App** нет вашего Bundle ID | Шаг 2, проверка ▶ на телефоне — потом обновите страницу |
| *«No suitable application records were found»* при отправке | Карточка (шаг 3) не создана или Bundle ID в ней другой |
| *«The name … is already being used»* | Другое название в шаге 3 |
| Apple отклонил сборку | Пришлите текст письма — подскажу, что исправить |
