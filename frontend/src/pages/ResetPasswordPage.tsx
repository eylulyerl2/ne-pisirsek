import { useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ErrorNote, Spinner } from "../components/Feedback";
import { Icon } from "../components/Icon";
import { usePreviewPasswordReset } from "../hooks/queries";
import { useAuth } from "../hooks/useAuth";
import { api } from "../services/endpoints";
import type { PasswordResetPreview } from "../services/types";

const UNUSABLE: Record<Exclude<PasswordResetPreview["status"], "pending">, string> = {
  used: "Bu şifre sıfırlama bağlantısı daha önce kullanılmış. Yeni bir sıfırlama için aile yöneticinize başvurun.",
  expired: "Bağlantının süresi dolmuş. Aile yöneticinizden yeni bir bağlantı ve şifre isteyin.",
  locked: "Çok fazla yanlış şifre denendiği için bağlantı kilitlendi. Aile yöneticinizden yeni bir bağlantı isteyin.",
};

/** Yöneticinin ürettiği bağlantının açıldığı herkese açık sayfa: /sifre-sifirla?kod=... */
export function ResetPasswordPage() {
  const [params] = useSearchParams();
  const token = params.get("kod");
  const navigate = useNavigate();
  const { completeLogin, loading } = useAuth();
  const preview = usePreviewPasswordReset(token);

  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [again, setAgain] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!token) return;
    if (password !== again) {
      setError(new Error("Şifreler aynı değil"));
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const { access_token } = await api.completePasswordReset({ token, code, new_password: password });
      await completeLogin(access_token);
      navigate("/plan", { replace: true });
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  }

  const data = preview.data;
  const notFound = !token || (preview.isError && (preview.error as { status?: number }).status === 404);

  return (
    <div className="auth-wrap">
      <div className="card auth-card" style={{ maxWidth: 460 }}>
        <div className="brand">
          <span className="brand-mark">
            <Icon name="pot" size={20} />
          </span>
          Ne Pişirsek?
        </div>
        <h1>Şifre yenileme</h1>

        {(loading || (token && preview.isPending)) && <Spinner />}

        {notFound && (
          <>
            <p className="sub">Bu bağlantı bulunamadı. Bağlantıyı eksiksiz kopyaladığınızdan emin olun.</p>
            <p className="auth-foot">
              <Link to="/giris">Giriş sayfasına git</Link>
            </p>
          </>
        )}
        {preview.isError && !notFound && <ErrorNote error={preview.error} onRetry={() => preview.refetch()} />}

        {data && !loading && (
          <>
            <p className="sub">
              <strong>{data.full_name}</strong>
              {data.username ? ` (@${data.username})` : ""} için yeni şifre belirleyin.
            </p>

            {!data.usable && data.status !== "pending" && (
              <div className="banner" role="alert">
                {UNUSABLE[data.status]}
              </div>
            )}

            {data.usable && (
              <form className="form" onSubmit={submit} noValidate>
                <div className="field">
                  <label htmlFor="reset-code">Sıfırlama şifresi (6 haneli)</label>
                  <input
                    id="reset-code"
                    className="input code-input"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    placeholder="000 000"
                    maxLength={7}
                    value={code}
                    onChange={(event) => setCode(event.target.value)}
                  />
                  <span className="hint">Şifreyi size bağlantıyı gönderen aile yöneticisi verdi. Yalnızca bir kez kullanılabilir.</span>
                </div>
                <div className="field">
                  <label htmlFor="reset-new">Yeni şifre</label>
                  <input id="reset-new" className="input" type="password" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} />
                  <span className="hint">En az 8 karakter. Bunu unutmayın: e-posta olmadan şifre kendiliğinden sıfırlanamaz.</span>
                </div>
                <div className="field">
                  <label htmlFor="reset-again">Yeni şifre (tekrar)</label>
                  <input id="reset-again" className="input" type="password" autoComplete="new-password" value={again} onChange={(e) => setAgain(e.target.value)} />
                </div>
                {error !== null && <ErrorNote error={error} />}
                <button type="submit" className="btn btn-primary" disabled={busy || !code.trim() || !password}>
                  {busy ? "Kaydediliyor…" : "Şifremi yenile ve giriş yap"}
                </button>
              </form>
            )}
          </>
        )}
      </div>
    </div>
  );
}
