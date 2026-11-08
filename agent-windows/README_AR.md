# NEON SENTINEL — درس Rust Agent الأول

**الإصدار:** Phase 2 / Lab MVP (تجريبي)

هذه النسخة عبارة عن برنامج Rust يعمل في نافذة PowerShell داخل Windows 11. ليست Windows Service، ولا تحتوي على مراقبة ملفات أو USB أو Clipboard، ولا تطبق منعاً، ولا تضم ذكاءً اصطناعياً حتى الآن.

## 1. ماذا يفعل Agent الآن؟

1. يقرأ اسم Windows الحقيقي من المتغير `COMPUTERNAME`.
2. ينشئ UUID عند أول تشغيل ويحفظه في `%LOCALAPPDATA%\NeonSentinel\device_id.txt`.
3. يرسل Heartbeat إلى سيرفر Linux. إن رجع `404`، يفهم أن الجهاز لم يُسجل ويُرسل طلب تسجيل ثم Heartbeat ثانياً.
4. يعيد Heartbeat كل **30 دقيقة** بعد النجاح، أو يعيد المحاولة بعد **60 ثانية** في حال انقطاع الاتصال أو حدوث خطأ.
5. مع الخيار `--once` ينفّذ دورة واحدة فقط ويغلق.
6. يخزن الأحداث الوصفية محلياً في `%LOCALAPPDATA%\NeonSentinel\events.sqlite3`؛ لا يرفعها إلى السيرفر.

> مهم: هذه النسخة لا تكتشف عودة الشبكة في منتصف النوم لمدة 30 دقيقة، ولا تجمع أحداث مراقبة. طابور SQLite محلي فقط، ولا يوجد رفع أحداث أو تطبيق سياسات.

## 2. لماذا Rust؟

Rust لغة مترجمة إلى ملف exe مستقل من دون الحاجة إلى مفسّر Python على جهاز العميل. وتستخدم نظام Ownership/Borrowing لحماية الذاكرة في كثير من الحالات من دون Garbage Collector. لكن استهلاك الموارد يتوقف أيضاً على الكود والمكتبات وآلية المراقبة.

- `Cargo.toml`: معلومات المشروع والمكتبات المطلوبة.
- `src/main.rs`: الكود التنفيذي للعميل.
- `Cargo`: أداة بناء واختبار المشروع.
- `rustc`: مترجم Rust.
- `rustup`: أداة تثبيت وإدارة نسخ Rust.

## 3. مطابق لسيرفر Flask الحالي

راجعنا `backend/main.py` في `DLP_REVIEW(1).zip`:

| طلب | النتيجة المتوقعة |
|---|---|
| `POST /api/v1/devices/register` | `201 Created`, وفي حالة UUID مكرر `409 Conflict` |
| `POST /api/v1/devices/{uuid}/heartbeat` | `200 OK`, وفي حالة جهاز غير مسجل `404 Not Found` |
| `GET /api/v1/devices` | قائمة جميع الأجهزة المسجّلة، بالمصادقة |

كل هذه المسارات تستخدم `Authorization: Bearer <token>`، والعنوان في المختبر `192.168.122.1:5000`.

## 4. أين نعمل؟

- Linux Mint: يبقى فيه السيرفر Python Flask وقاعدة SQLite والواجهة.
- Windows 11 VM: نبني ونشغّل Agent Rust أول مرة. وجود مجلد `agent-windows` في Linux **لا يجعله ظاهراً تلقائياً** داخل Windows VM.

إذا أردت الاحتفاظ بالكود مع مشروع Linux، انسخ المجلد إلى `~/Documents/DLP/agent-windows` لمراجعته وتحريره. انقل نسخة منه إلى Windows VM عبر مشاركة ملفات موثوقة أو حمّل ملف ZIP داخل Windows.

## 5. تثبيت أدوات Rust داخل Windows VM

1. من Microsoft ثبّت **Visual Studio C++ Build Tools** وحدد `Desktop development with C++`، إن لم تكن مثبتة.
2. من https://rust-lang.org/install نزّل نسخة Windows من `rustup-init.exe` وثبّتها بالإعدادات الافتراضية (MSVC).
3. افتح نافذة **PowerShell جديدة** ونفّذ:

```powershell
rustc --version
cargo --version
```

> أدوات الترجمة قد تتطلب مساحة وذاكرة ملحوظة عند البناء، لكن لا يحتاج المستخدم النهائي إلى تثبيتها لتشغيل EXE المبني.

## 6. استخراج الملفات وبناء Agent

افترض أن ZIP موجود في `Downloads` داخل Windows:

```powershell
$dest = "$env:USERPROFILE\Documents\NeonLab"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\NEON_SENTINEL_Rust_Agent_Phase2.zip" -DestinationPath $dest
cd "$dest\agent-windows"
cargo test
cargo build --release
```

إذا لم يتوفر اتصال إنترنت داخل Windows VM، سيحتاج Cargo إلى تنزيل المكتبات بطريقة أخرى أو إلى بيئة بناء ذات إنترنت؛ لا تحاول تجاهل فشل تثبيت المكتبات.

## 7. وضع مفتاح المصادقة في PowerShell دون حفظه بالكود

على Linux المفتاح محفوظ في `~/.config/neon-sentinel/api-token`. انقله إلى Windows **سراً**، ولا ترفعه إلى GitHub أو ChatGPT.

داخل PowerShell في Windows:

```powershell
$secure = Read-Host 'DLP lab token' -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
    $env:NEON_SENTINEL_API_TOKEN = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
}
Remove-Variable secure,ptr -ErrorAction SilentlyContinue
```

سيكون المفتاح متوفراً لبرنامج Rust الذي تشغّله من النافذة نفسها فقط. لا تحتفظ به داخل ملفات الكود.

## 8. أول اختبار

```powershell
.\target\release\neon-sentinel-agent.exe --once
```

في أول تشغيل ستحصل غالباً على `Device not registered` ثم `Device registration succeeded` ثم `Initial heartbeat accepted`.
عند تكرار الأمر سيعيد استخدام UUID نفسه، وغالباً يرسل Heartbeat فقط، ولا ينشئ جهازاً مكرراً.

## 9. اختبار طابور الأحداث المحلي

```powershell
.\target\release\neon-sentinel-agent.exe --demo-event
.\target\release\neon-sentinel-agent.exe --queue-status
```

ينشئ `--demo-event` حدثاً اصطناعياً ببيانات وصفية فقط. يعرض `--queue-status` إجمالي الأحداث والمعلّقة والمرسلة؛ لا تُرسل الأحداث إلى السيرفر في هذه المرحلة.

## 10. اختبار التشغيل الدوري

```powershell
.\target\release\neon-sentinel-agent.exe
```

- نجاح الاتصال: Heartbeat آخر بعد 30 دقيقة.
- خطأ اتصال: إعادة المحاولة بعد دقيقة.
- الإيقاف: `Ctrl+C`.
- لا يعمل تلقائياً عند بدء Windows، وليس خدمة Windows بعد.

## 11. التحقق من Linux

```bash
TOKEN="$(cat ~/.config/neon-sentinel/api-token)"
curl -sS -H "Authorization: Bearer $TOKEN" http://192.168.122.1:5000/api/v1/devices | python3 -m json.tool
```

ستظهر الأجهزة التجريبية `WIN-LAB-DEMO` القديمة أيضاً، بالإضافة إلى الاسم الحقيقي القادم من Windows.

## 11. ما الذي سنضيفه في المراحل التالية؟

- قاعدة SQLite محلية **للأحداث**، بصف انتظار مع Event ID ووقت الحدث ووقت التسليم وACK من السيرفر.
- Policy Cache مع إصدار السياسة والتحقق منها.
- أحداث مراقبة محددة ومصرّح بها على Windows (ملفات/USB/Clipboard وفق قدرات Win32 المتاحة).
- إرسال Critical Alerts فورياً عند توفر الشبكة.
- TLS ومفاتيح مستقلة لكل جهاز وتخزين آمن للأسرار.
- Windows Service مُدارة مع إيقاف وإزالة إداريين مصرح بهما.

## ملاحظات تقنية وأمنية

- **مختبر معزول فقط**: HTTP ينقل Bearer Token من دون تشفير، والمفتاح الحالي مشترك، فلا تستخدم هذه النسخة على شبكة غير موثوقة أو مع بيانات شخصية حقيقية.
- قيمة `platform` المرسلة الآن هي `Windows`، لأن `std::env` وحده لا يحدد إصدار Windows بدقة. سنضيف كشف إصدار النظام لاحقاً.
- الملف `device_id.txt` ليس ملف سر؛ لكن حذفه سيؤدي إلى إنشاء هوية مختلفة في التشغيل التالي.
- راجع الاستهلاك الفعلي في Task Manager. لا توجد ضمانات لحجم RAM/CPU قبل القياس.
- تم فحص العقد البرمجي مقابل ملفات Flask المرفوعة، لكن **تعذّر تجميع Rust في بيئة إعداد الدرس**. مطلوب تشغيل `cargo test` و`cargo build --release` داخل Windows VM وإرسال الأخطاء إن ظهرت.

مصادر التعلّم الرسمية:
- https://doc.rust-lang.org/book/
- https://rust-lang.org/install
- https://learn.microsoft.com/en-us/windows/dev-environment/rust/setup
