# HR + CRM Arabic brief (RAQEEM, V1.3)

Goal: every HR (hrms) and CRM string reads as clear, professional Modern Standard Arabic,
as a Libyan/Arab business would expect in a polished ERP. Consistent terms, no machine-translation feel.

## Input: `in/Bxx.tsv` (tab separated, escaped: `\n` `\t` `\\`)
`key  app  context  English  current-Arabic` (current Arabic may be empty or poor)

## Output: `out/Bxx.tsv` — one line per input key, same order, nothing else
`key<TAB>Arabic`   (keep the same escaping: a real newline in the text is written `\n`)

## Rules
1. Read `raqim_sales/raqim_sales/translations/glossary.md` fully first (all sections, especially
   "HR — الموارد البشرية" and "CRM — إدارة العملاء"). Its terms are mandatory.
   Submit = «اعتماد», Approve = «الموافقة». Lead = «عميل محتمل», Deal = «صفقة».
2. Keep good current Arabic as is; fix it when it is wrong, literal, awkward, inconsistent with
   the glossary, or uses odd wording such as «تم + مصدر» chains, «الخاص بـ» overuse, transliterations.
3. Placeholders and markup must survive EXACTLY, same count each: `{0}` `{1}` `{}` `{name}`
   `%s` `%d` `%(x)s` `<b>` `</b>` `<br>` `<a href="...">` and every other `<tag>`, `&nbsp;`.
   Never translate inside them. Order may change to fit Arabic grammar.
4. Labels/buttons/column headers: short noun phrases, no full stop. Messages: full sentences,
   Arabic punctuation (، ؛ ؟). Use Western digits as in the English.
5. Keep brand/product names in Latin: Frappe, ERPNext, Twilio, Exotel, Gmail, Google, Razorpay.
   WhatsApp → «واتساب» in sentences. Acronyms like SLA, KRA, PAN, PF, ESI may stay Latin.
6. Indian-payroll specific terms (PF, ESI, HRA, PAN, TDS, Gratuity Rule…) — translate the words,
   keep the acronym: e.g. «إعفاء بدل السكن (HRA)».
7. Plural-aware where possible: «{0} موظفين» is fine; avoid «(ات)» bracket hacks.
8. Gender-neutral imperatives in buttons: use masdar («إضافة موظف», «حفظ») not «أضف».
9. Never leave a line empty; if the English is a code/identifier (e.g. `{0}: {1}`, `UTC`, a URL),
   copy it unchanged.
10. No tashkeel except where it removes real ambiguity (e.g. «المُقابِل»).
