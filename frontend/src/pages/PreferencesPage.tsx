import { useEffect, useState, type FormEvent } from "react";
import { ErrorNote, Spinner } from "../components/Feedback";
import { usePreferences, useUpdatePreferences } from "../hooks/queries";
import { useAuth } from "../hooks/useAuth";
import { api } from "../services/endpoints";
import type { Preferences } from "../services/types";

interface FormState {
  full_name: string;
  servings_per_meal: string;
  soup_frequency_per_week: string;
  vegetable_frequency_per_week: string;
  legume_frequency_per_week: string;
  daily_calorie_target: string;
  max_preparation_time_minutes: string;
  weekly_budget: string;
}

const text = (value: number | null) => (value === null ? "" : String(value));
const optionalNumber = (value: string) => (value.trim() === "" ? null : Number(value));

function fromPreferences(name: string, p: Preferences): FormState {
  return {
    full_name: name,
    servings_per_meal: String(p.servings_per_meal),
    soup_frequency_per_week: String(p.soup_frequency_per_week),
    vegetable_frequency_per_week: String(p.vegetable_frequency_per_week),
    legume_frequency_per_week: String(p.legume_frequency_per_week),
    daily_calorie_target: text(p.daily_calorie_target),
    max_preparation_time_minutes: text(p.max_preparation_time_minutes),
    weekly_budget: text(p.weekly_budget),
  };
}

function ChangePasswordSection() {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [again, setAgain] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setDone(false);
    if (next !== again) {
      setError(new Error("Yeni şifreler aynı değil"));
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.changePassword({ current_password: current, new_password: next });
      setCurrent("");
      setNext("");
      setAgain("");
      setDone(true);
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card card-pad form" onSubmit={submit} noValidate aria-label="Şifre değiştir">
      <h2>Şifre değiştir</h2>
      <div className="form-grid">
        <div className="field">
          <label htmlFor="current-password">Mevcut şifre</label>
          <input id="current-password" className="input" type="password" autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="new-password">Yeni şifre</label>
          <input id="new-password" className="input" type="password" autoComplete="new-password" value={next} onChange={(e) => setNext(e.target.value)} />
          <span className="hint">En az 8 karakter.</span>
        </div>
        <div className="field">
          <label htmlFor="new-password-again">Yeni şifre (tekrar)</label>
          <input id="new-password-again" className="input" type="password" autoComplete="new-password" value={again} onChange={(e) => setAgain(e.target.value)} />
        </div>
      </div>
      {error !== null && <ErrorNote error={error} />}
      {done && (
        <div className="banner banner-info" role="status">
          Şifreniz değiştirildi.
        </div>
      )}
      <div>
        <button type="submit" className="btn" disabled={busy || !current || !next}>
          {busy ? "Kaydediliyor…" : "Şifreyi değiştir"}
        </button>
      </div>
    </form>
  );
}

export function PreferencesPage() {
  const { user, setUser } = useAuth();
  const preferences = usePreferences();
  const update = useUpdatePreferences();
  const [form, setForm] = useState<FormState | null>(null);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (preferences.data && user && form === null) setForm(fromPreferences(user.full_name, preferences.data));
  }, [preferences.data, user, form]);

  function set<K extends keyof FormState>(key: K, value: string) {
    setForm((current) => (current ? { ...current, [key]: value } : current));
    setSaved(false);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!form || !user) return;
    setSaving(true);
    setError(null);
    try {
      if (form.full_name.trim() !== user.full_name) setUser(await api.updateProfile({ full_name: form.full_name }));
      await update.mutateAsync({
        servings_per_meal: Number(form.servings_per_meal),
        soup_frequency_per_week: Number(form.soup_frequency_per_week),
        vegetable_frequency_per_week: Number(form.vegetable_frequency_per_week),
        legume_frequency_per_week: Number(form.legume_frequency_per_week),
        daily_calorie_target: optionalNumber(form.daily_calorie_target),
        max_preparation_time_minutes: optionalNumber(form.max_preparation_time_minutes),
        weekly_budget: optionalNumber(form.weekly_budget),
      });
      setSaved(true);
    } catch (caught) {
      setError(caught);
    } finally {
      setSaving(false);
    }
  }

  if (preferences.isPending || (preferences.data && !form)) return <Spinner />;
  if (preferences.error) return <ErrorNote error={preferences.error} onRetry={() => preferences.refetch()} />;
  if (!form) return null;

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>Tercihler</h1>
          <p>Haftalık menü bu tercihlere göre hazırlanır.</p>
        </div>
      </div>

      <form className="form" onSubmit={submit} noValidate>
        <section className="card card-pad form">
          <h2>Profil</h2>
          <div className="field">
            <label htmlFor="full_name">Ad soyad</label>
            <input id="full_name" className="input" value={form.full_name} onChange={(e) => set("full_name", e.target.value)} maxLength={100} />
          </div>
        </section>

        <section className="card card-pad form">
          <h2>Sofranız</h2>
          <div className="form-grid">
            <NumberField id="servings_per_meal" label="Öğün başına kişi sayısı" value={form.servings_per_meal} min={1} max={20} onChange={(v) => set("servings_per_meal", v)} hint="Alışveriş miktarları bu sayıya göre hesaplanır." />
            <NumberField id="soup" label="Haftada kaç gün çorba?" value={form.soup_frequency_per_week} min={0} max={7} onChange={(v) => set("soup_frequency_per_week", v)} />
            <NumberField id="veg" label="Haftada kaç gün sebze yemeği?" value={form.vegetable_frequency_per_week} min={0} max={7} onChange={(v) => set("vegetable_frequency_per_week", v)} />
            <NumberField id="legume" label="Haftada kaç gün baklagil?" value={form.legume_frequency_per_week} min={0} max={7} onChange={(v) => set("legume_frequency_per_week", v)} hint="Kuru fasulye, nohut, mercimek gibi." />
          </div>
        </section>

        <section className="card card-pad form">
          <h2>Sınırlar</h2>
          <p className="muted small">Boş bırakırsanız sınır uygulanmaz.</p>
          <div className="form-grid">
            <NumberField id="calories" label="Günlük kalori hedefi (kcal)" value={form.daily_calorie_target} min={500} max={10000} placeholder="örn. 2000" onChange={(v) => set("daily_calorie_target", v)} />
            <NumberField id="time" label="En uzun yemek süresi (dk)" value={form.max_preparation_time_minutes} min={1} placeholder="örn. 60" onChange={(v) => set("max_preparation_time_minutes", v)} />
            <NumberField id="budget" label="Haftalık bütçe (₺)" value={form.weekly_budget} min={0} placeholder="örn. 1500" onChange={(v) => set("weekly_budget", v)} />
          </div>
        </section>

        {error !== null && <ErrorNote error={error} />}
        {saved && (
          <div className="banner banner-info" role="status">
            Tercihleriniz kaydedildi. Yeni menü oluşturduğunuzda geçerli olur.
          </div>
        )}
        <div>
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? "Kaydediliyor…" : "Kaydet"}
          </button>
        </div>
      </form>

      <ChangePasswordSection />
    </div>
  );
}

interface NumberFieldProps {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  min?: number;
  max?: number;
  placeholder?: string;
  hint?: string;
}

function NumberField({ id, label, value, onChange, min, max, placeholder, hint }: NumberFieldProps) {
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        className="input"
        type="number"
        inputMode="numeric"
        min={min}
        max={max}
        placeholder={placeholder}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        aria-describedby={hint ? `${id}-hint` : undefined}
      />
      {hint && (
        <span className="hint" id={`${id}-hint`}>
          {hint}
        </span>
      )}
    </div>
  );
}
