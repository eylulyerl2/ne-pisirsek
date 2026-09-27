/** Sayfalar arası gezinirken korunacak adres parametrelerini ("?hafta=…&aile=…") üretir. */
export function keepParams(search: string, names: string[] = ["hafta", "aile"]): string {
  const source = new URLSearchParams(search);
  const kept = new URLSearchParams();
  for (const name of names) {
    const value = source.get(name);
    if (value) kept.set(name, value);
  }
  const text = kept.toString();
  return text ? `?${text}` : "";
}

export function inviteLink(token: string, origin = window.location.origin): string {
  return `${origin}/katil?kod=${encodeURIComponent(token)}`;
}

/** 482917 -> "482 917" (okunması ve söylenmesi kolay) */
export function formatCode(code: string): string {
  return code.length === 6 ? `${code.slice(0, 3)} ${code.slice(3)}` : code;
}

/** Davet edilecek kişiye gönderilecek hazır mesaj. */
export function inviteMessage(familyName: string, token: string, code: string, origin = window.location.origin): string {
  return `${familyName} ailesine katıl:\n${inviteLink(token, origin)}\nŞifre: ${formatCode(code)}`;
}

export function resetLink(token: string, origin = window.location.origin): string {
  return `${origin}/sifre-sifirla?kod=${encodeURIComponent(token)}`;
}

/** Şifresini yenileyecek kişiye gönderilecek hazır mesaj. */
export function resetMessage(token: string, code: string, origin = window.location.origin): string {
  return `Şifreni yenilemek için:\n${resetLink(token, origin)}\nŞifre: ${formatCode(code)}`;
}
