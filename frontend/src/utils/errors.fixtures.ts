// Backend'in (FastAPI/pydantic) gerçek 422 gövdelerinden alınmış örnekler.
export const formatErrorFixtures = [
  {
    name: "geçersiz e-posta",
    status: 422,
    payload: { detail: [{ type: "value_error", loc: ["body", "email"], msg: "value is not a valid email address: An email address must have an @-sign." }] },
    expected: "Geçerli bir e-posta adresi girin",
  },
  {
    name: "kısa şifre",
    status: 422,
    payload: { detail: [{ type: "string_too_short", loc: ["body", "password"], msg: "String should have at least 8 characters", ctx: { min_length: 8 } }] },
    expected: "Şifre en az 8 karakter olmalı",
  },
  {
    name: "eksik alan",
    status: 422,
    payload: { detail: [{ type: "missing", loc: ["body", "full_name"], msg: "Field required" }] },
    expected: "Ad soyad zorunlu",
  },
  {
    name: "sayı aralığı (kalori)",
    status: 422,
    payload: { detail: [{ type: "greater_than_equal", loc: ["body", "daily_calorie_target"], msg: "Input should be greater than or equal to 500", ctx: { ge: 500 } }] },
    expected: "Günlük kalori hedefi en az 500 olmalı",
  },
  {
    name: "sunucunun kendi Türkçe doğrulama mesajı",
    status: 422,
    payload: { detail: [{ type: "value_error", loc: ["body", "week_start_date"], msg: "Value error, Hafta başlangıcı Pazartesi olmalı" }] },
    expected: "Hafta başlangıcı Pazartesi olmalı",
  },
  {
    name: "aynı hata birden çok kez gelirse tekrarlanmaz",
    status: 422,
    payload: {
      detail: [
        { type: "missing", loc: ["body", "email"], msg: "Field required" },
        { type: "missing", loc: ["body", "email"], msg: "Field required" },
        { type: "missing", loc: ["body", "password"], msg: "Field required" },
      ],
    },
    expected: "E-posta zorunlu. Şifre zorunlu",
  },
  {
    name: "bilinmeyen alan ve tür",
    status: 422,
    payload: { detail: [{ type: "something_new", loc: ["body", "xyz"], msg: "boom" }] },
    expected: "Bu alan geçersiz",
  },
];
