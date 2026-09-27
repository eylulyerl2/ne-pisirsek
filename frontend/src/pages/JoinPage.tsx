import { useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ErrorNote, Spinner } from "../components/Feedback";
import { Icon } from "../components/Icon";
import { useAcceptInvitation, usePreviewInvitation } from "../hooks/queries";
import { useAuth } from "../hooks/useAuth";
import { api } from "../services/endpoints";
import type { InvitationPreview } from "../services/types";

const UNUSABLE: Record<Exclude<InvitationPreview["status"], "pending">, string> = {
  accepted: "Bu davet daha önce kullanılmış. Her davet yalnızca bir kişi içindir; aile yöneticisinden yeni bir davet isteyin.",
  expired: "Davetin süresi dolmuş. Aile yöneticisinden yeni bir bağlantı ve şifre isteyin.",
  locked: "Çok fazla yanlış şifre denendiği için davet kilitlendi. Aile yöneticisinden yeni bir şifre isteyin.",
};

type Mode = "new" | "existing";

/** Davet bağlantısının açıldığı herkese açık sayfa: /katil?kod=... */
export function JoinPage() {
  const [params] = useSearchParams();
  const token = params.get("kod");
  const navigate = useNavigate();
  const { user, loading, login, completeLogin, logout } = useAuth();
  const preview = usePreviewInvitation(token);
  const accept = useAcceptInvitation();

  const [mode, setMode] = useState<Mode>("new");
  const [code, setCode] = useState("");
  const [fullName, setFullName] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [email, setEmail] = useState("");
  const [identifier, setIdentifier] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function run(action: () => Promise<string>) {
    setBusy(true);
    setError(null);
    try {
      navigate(`/aile/${await action()}`, { replace: true });
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  }

  function submitNew(event: FormEvent) {
    event.preventDefault();
    if (!token) return;
    void run(async () => {
      const result = await api.joinWithNewAccount({
        token,
        code,
        full_name: fullName,
        username,
        password,
        ...(email.trim() ? { email: email.trim() } : {}),
      });
      await completeLogin(result.access_token);
      return result.family.family_id;
    });
  }

  function submitExisting(event: FormEvent) {
    event.preventDefault();
    if (!token) return;
    void run(async () => {
      if (!user) await login(identifier, password);
      const family = await accept.mutateAsync({ token, code });
      return family.family_id;
    });
  }

  const data = preview.data;
  const notFound = !token || (preview.isError && (preview.error as { status?: number }).status === 404);

  return (
    <div className="auth-wrap">
      <div className="card auth-card" style={{ maxWidth: 480 }}>
        <div className="brand">
          <span className="brand-mark">
            <Icon name="pot" size={20} />
          </span>
          Ne Pişirsek?
        </div>
        <h1>Aile daveti</h1>

        {(loading || (token && preview.isPending)) && <Spinner />}

        {notFound && (
          <>
            <p className="sub">Bu davet bulunamadı. Bağlantıyı eksiksiz kopyaladığınızdan emin olun.</p>
            <p className="auth-foot">
              <Link to="/giris">Giriş sayfasına git</Link>
            </p>
          </>
        )}
        {preview.isError && !notFound && <ErrorNote error={preview.error} onRetry={() => preview.refetch()} />}

        {data && !loading && (
          <>
            <p className="sub">
              {data.label ? `Merhaba ${data.label}! ` : ""}
              <strong>{data.inviter_name}</strong> sizi <strong>{data.family_name}</strong> ailesine davet ediyor.
            </p>

            {!data.usable && data.status !== "pending" && (
              <div className="banner" role="alert">
                {UNUSABLE[data.status]}
              </div>
            )}

            {data.usable && (
              <div className="stack">
                <div className="field">
                  <label htmlFor="join-code">Davet şifresi (6 haneli)</label>
                  <input
                    id="join-code"
                    className="input code-input"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    placeholder="000 000"
                    maxLength={7}
                    value={code}
                    onChange={(event) => setCode(event.target.value)}
                  />
                  <span className="hint">Şifreyi sizi davet eden kişi verdi. Yalnızca bir kez kullanılabilir.</span>
                </div>

                {user ? (
                  <form className="form" onSubmit={submitExisting} noValidate>
                    <p>
                      <strong>{user.full_name}</strong> hesabıyla katılacaksınız.
                    </p>
                    {error !== null && <ErrorNote error={error} />}
                    {!busy && !code.trim() && <p className="hint">Devam etmek için yukarıya davet şifresini girin.</p>}
                    <button type="submit" className="btn btn-primary" disabled={busy || !code.trim()}>
                      {busy ? "Katılınıyor…" : "Aileye katıl"}
                    </button>
                    <button type="button" className="btn btn-ghost btn-sm" onClick={logout}>
                      Başka bir hesapla devam et
                    </button>
                  </form>
                ) : (
                  <>
                    <div className="tabs" role="tablist" aria-label="Hesap durumu">
                      <button type="button" role="tab" aria-selected={mode === "new"} onClick={() => { setMode("new"); setError(null); }}>
                        Yeni hesap oluştur
                      </button>
                      <button type="button" role="tab" aria-selected={mode === "existing"} onClick={() => { setMode("existing"); setError(null); }}>
                        Hesabım var
                      </button>
                    </div>

                    {mode === "new" ? (
                      <form className="form" onSubmit={submitNew} noValidate>
                        <div className="field">
                          <label htmlFor="join-name">Ad soyad</label>
                          <input id="join-name" className="input" autoComplete="name" maxLength={100} value={fullName} onChange={(e) => setFullName(e.target.value)} />
                        </div>
                        <div className="field">
                          <label htmlFor="join-username">Kullanıcı adı</label>
                          <input id="join-username" className="input" autoCapitalize="none" spellCheck={false} autoComplete="username" maxLength={30} value={username} onChange={(e) => setUsername(e.target.value)} />
                          <span className="hint">Giriş yaparken kullanacaksınız. Küçük harf (a-z), rakam, nokta, tire ve alt çizgi; en az 3 karakter.</span>
                        </div>
                        <div className="field">
                          <label htmlFor="join-password">Şifre</label>
                          <input id="join-password" className="input" type="password" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} />
                          <span className="hint">En az 8 karakter. Bunu unutmayın: e-posta olmadan şifre sıfırlanamaz.</span>
                        </div>
                        <div className="field">
                          <label htmlFor="join-email">E-posta (isteğe bağlı)</label>
                          <input id="join-email" className="input" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} />
                          <span className="hint">E-postanız yoksa boş bırakın.</span>
                        </div>
                        {error !== null && <ErrorNote error={error} />}
                        {!busy && !code.trim() && <p className="hint">Devam etmek için yukarıya davet şifresini girin.</p>}
                        <button type="submit" className="btn btn-primary" disabled={busy || !code.trim()}>
                          {busy ? "Hesap oluşturuluyor…" : "Hesap oluştur ve katıl"}
                        </button>
                      </form>
                    ) : (
                      <form className="form" onSubmit={submitExisting} noValidate>
                        <div className="field">
                          <label htmlFor="join-identifier">E-posta veya kullanıcı adı</label>
                          <input id="join-identifier" className="input" autoCapitalize="none" spellCheck={false} autoComplete="username" value={identifier} onChange={(e) => setIdentifier(e.target.value)} />
                        </div>
                        <div className="field">
                          <label htmlFor="join-existing-password">Şifre</label>
                          <input id="join-existing-password" className="input" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} />
                        </div>
                        {error !== null && <ErrorNote error={error} />}
                        {!busy && !code.trim() && <p className="hint">Devam etmek için yukarıya davet şifresini girin.</p>}
                        <button type="submit" className="btn btn-primary" disabled={busy || !code.trim()}>
                          {busy ? "Katılınıyor…" : "Giriş yap ve katıl"}
                        </button>
                      </form>
                    )}
                  </>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
