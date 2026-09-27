import { describe, expect, it } from "vitest";
import { addDays, dayName, formatWeekRange, mondayOf, parseISODate, toISODate } from "./dates";
import { formatErrorFixtures } from "./errors.fixtures";
import { formatAmount, formatDuration, formatMoney, formatQuantity, formatShoppingAmount, scaleQuantity } from "./format";
import { formatApiError } from "./errors";

describe("tarih yardımcıları", () => {
  it("haftanın Pazartesi'sini bulur", () => {
    expect(toISODate(mondayOf(parseISODate("2026-09-30")))).toBe("2026-09-28"); // Çarşamba
    expect(toISODate(mondayOf(parseISODate("2026-10-04")))).toBe("2026-09-28"); // Pazar
    expect(toISODate(mondayOf(parseISODate("2026-09-28")))).toBe("2026-09-28"); // Pazartesi
  });

  it("ay ve yıl sınırlarını doğru geçer", () => {
    expect(toISODate(addDays(parseISODate("2026-09-28"), 7))).toBe("2026-10-05");
    expect(toISODate(addDays(parseISODate("2025-12-29"), 7))).toBe("2026-01-05");
    expect(toISODate(addDays(parseISODate("2026-03-01"), -1))).toBe("2026-02-28");
  });

  it("gün kayması yaşamadan yerel tarihi yazar", () => {
    expect(toISODate(new Date(2026, 0, 1, 23, 59))).toBe("2026-01-01");
    expect(toISODate(new Date(2026, 0, 1, 0, 0))).toBe("2026-01-01");
  });

  it("Türkçe hafta aralığı ve gün adı üretir", () => {
    expect(formatWeekRange(parseISODate("2026-09-28"))).toBe("28 Eylül – 4 Ekim 2026");
    expect(formatWeekRange(parseISODate("2025-12-29"))).toBe("29 Aralık 2025 – 4 Ocak 2026");
    expect(dayName(1)).toBe("Pazartesi");
    expect(dayName(7)).toBe("Pazar");
  });
});

describe("biçim yardımcıları", () => {
  it("para ve süre", () => {
    expect(formatMoney(1240)).toBe("₺1.240");
    expect(formatMoney(null)).toBe("—");
    expect(formatMoney(99.6)).toBe("₺100");
    expect(formatDuration(45)).toBe("45 dk");
    expect(formatDuration(80)).toBe("1 sa 20 dk");
    expect(formatDuration(120)).toBe("2 sa");
    expect(formatDuration(0)).toBe("—");
  });

  it("miktarı kesirlerle yazar", () => {
    expect(formatQuantity(0.5)).toBe("½");
    expect(formatQuantity(1.5)).toBe("1½");
    expect(formatQuantity(0.75)).toBe("¾");
    expect(formatQuantity(2)).toBe("2");
    expect(formatQuantity(2.667)).toBe("2⅔");
    expect(formatQuantity(2.4)).toBe("2,4");
    expect(formatQuantity(250)).toBe("250");
  });

  it("birimleri okunur hale getirir", () => {
    expect(formatAmount(1500, "g")).toBe("1,5 kg");
    expect(formatAmount(300, "g")).toBe("300 g");
    expect(formatAmount(2.5, "g")).toBe("2,5 g");
    expect(formatAmount(83.333, "ml")).toBe("83,33 ml");
    expect(formatAmount(1000, "ml")).toBe("1 L");
    expect(formatAmount(1, "yk")).toBe("1 yemek kaşığı");
    expect(formatAmount(0.5, "ck")).toBe("½ çay kaşığı");
    expect(formatAmount(3, "adet")).toBe("3 adet");
    expect(formatAmount(null, null)).toBe("");
  });

  it("alışveriş miktarlarını satın alınabilir biçimde yukarı yuvarlar", () => {
    expect(formatShoppingAmount(1.333, "adet")).toBe("2 adet");
    expect(formatShoppingAmount(3, "adet")).toBe("3 adet");
    expect(formatShoppingAmount(0.3, "adet")).toBe("1 adet");
    expect(formatShoppingAmount(83.33, "g")).toBe("85 g");
    expect(formatShoppingAmount(300, "g")).toBe("300 g");
    expect(formatShoppingAmount(2.5, "g")).toBe("3 g");
    expect(formatShoppingAmount(1020, "g")).toBe("1,02 kg");
    expect(formatShoppingAmount(83.33, "ml")).toBe("85 ml");
    expect(formatShoppingAmount(7.83, "ck")).toBe("8 çay kaşığı");
    expect(formatShoppingAmount(0.75, "demet")).toBe("1 demet");
    expect(formatShoppingAmount(2.33, "demet")).toBe("2½ demet");
    expect(formatShoppingAmount(4.33, "yk")).toBe("4½ yemek kaşığı");
    expect(formatShoppingAmount(5, "diş")).toBe("5 diş");
    expect(formatShoppingAmount(null, "g")).toBe("");
  });

  it("porsiyona göre ölçekler", () => {
    expect(scaleQuantity(300, 4, 2)).toBe(150);
    expect(scaleQuantity(1, 4, 6)).toBe(1.5);
    expect(scaleQuantity(null, 4, 2)).toBeNull();
  });
});

describe("API hata mesajları", () => {
  it("metin detayını olduğu gibi döndürür", () => {
    expect(formatApiError(409, { detail: "Bu e-posta adresi zaten kayıtlı" })).toBe("Bu e-posta adresi zaten kayıtlı");
  });

  it.each(formatErrorFixtures)("$name", ({ status, payload, expected }) => {
    expect(formatApiError(status, payload)).toBe(expected);
  });

  it("gövde yoksa duruma göre Türkçe mesaj verir", () => {
    expect(formatApiError(401, null)).toContain("Oturumunuz");
    expect(formatApiError(403, null)).toContain("yetkiniz");
    expect(formatApiError(404, {})).toContain("bulunamadı");
    expect(formatApiError(500, null)).toContain("Sunucuda");
    expect(formatApiError(418, null)).toBe("İşlem tamamlanamadı");
  });
});
