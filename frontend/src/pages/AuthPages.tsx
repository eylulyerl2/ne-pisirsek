import { useState, type FormEvent } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { ErrorNote } from "../components/Feedback";
import { Icon } from "../components/Icon";
import { useAuth } from "../hooks/useAuth";

function AuthShell({ title, subtitle, children, footer }: { title: string; subtitle: string; children: React.ReactNode; footer: React.ReactNode }) {
  return (
    <div className="auth-wrap">
      <div className="card auth-card">
        <div className="brand">
          <span className="brand-mark">
            <Icon name="pot" size={20} />
          </span>
          Ne Pişirsek?
        </div>
        <h1>{title}</h1>
        <p className="sub">{subtitle}</p>
        {children}
        <p className="auth-foot">{footer}</p>
      </div>
    </div>
  );
}

function useAfterAuth() {
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from;
  return from && from.startsWith("/") ? from : "/plan";
}

export function LoginPage() {
  const location = useLocation();
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const target = useAfterAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to={target} replace />;

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
      navigate(target, { replace: true });
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell
      title="Tekrar hoş geldiniz"
      subtitle="Hesabınıza giriş yapın."
      footer={
        <>
          Hesabınız yok mu? <Link to="/kayit" state={location.state}>Kayıt olun</Link>
        </>
      }
    >
      <form className="form" onSubmit={submit} noValidate>
        <div className="field">
          <label htmlFor="identifier">E-posta veya kullanıcı adı</label>
          <input id="identifier" className="input" type="text" autoComplete="username" autoCapitalize="none" spellCheck={false} required value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="password">Şifre</label>
          <input id="password" className="input" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
        </div>
        {error !== null && <ErrorNote error={error} />}
        <button type="submit" className="btn btn-primary" disabled={busy}>
          {busy ? "Giriş yapılıyor…" : "Giriş yap"}
        </button>
        <p className="muted small" style={{ textAlign: "center" }}>
          Şifrenizi mi unuttunuz? Aile yöneticinizden şifre sıfırlama bağlantısı isteyin.
        </p>
      </form>
    </AuthShell>
  );
}

export function RegisterPage() {
  const location = useLocation();
  const { user, register } = useAuth();
  const navigate = useNavigate();
  const target = useAfterAuth();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to={target} replace />;

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!fullName.trim()) {
      setError(new Error("Ad soyad zorunlu"));
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await register(fullName, email, password);
      navigate(target, { replace: true });
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell
      title="Hesap oluşturun"
      subtitle="Ailenizin haftalık menüsünü birlikte planlayın."
      footer={
        <>
          Zaten hesabınız var mı? <Link to="/giris" state={location.state}>Giriş yapın</Link>
        </>
      }
    >
      <form className="form" onSubmit={submit} noValidate>
        <div className="field">
          <label htmlFor="full_name">Ad soyad</label>
          <input id="full_name" className="input" autoComplete="name" required maxLength={100} value={fullName} onChange={(e) => setFullName(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="email">E-posta</label>
          <input id="email" className="input" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="password">Şifre</label>
          <input id="password" className="input" type="password" autoComplete="new-password" minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} aria-describedby="password-hint" />
          <span className="hint" id="password-hint">
            En az 8 karakter.
          </span>
        </div>
        {error !== null && <ErrorNote error={error} />}
        <button type="submit" className="btn btn-primary" disabled={busy}>
          {busy ? "Hesap oluşturuluyor…" : "Kayıt ol"}
        </button>
      </form>
    </AuthShell>
  );
}
