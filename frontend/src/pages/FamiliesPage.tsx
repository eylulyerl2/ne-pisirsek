import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { EmptyState, ErrorNote, Spinner } from "../components/Feedback";
import { useCreateFamily, useFamilies } from "../hooks/queries";

export function FamiliesPage() {
  const families = useFamilies();
  const create = useCreateFamily();
  const [name, setName] = useState("");

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;
    create.mutate(name, { onSuccess: () => setName("") });
  }

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>Aile</h1>
          <p>Ailenizle aynı menüyü planlayın, alışveriş listesini paylaşın.</p>
        </div>
      </div>

      <section className="stack" aria-label="Ailelerim">
        <h2>Ailelerim</h2>
        {families.isPending && <Spinner />}
        {families.error && <ErrorNote error={families.error} onRetry={() => families.refetch()} />}
        {families.data?.length === 0 && (
          <div className="card card-pad">
            <EmptyState title="Henüz bir ailede değilsiniz">
              <p>Aşağıdan yeni bir aile oluşturun. Başkasının ailesine katılmak için size verilen davet bağlantısını açıp şifreyi girin.</p>
            </EmptyState>
          </div>
        )}
        <div className="meal-grid">
          {families.data?.map((family) => (
            <div key={family.family_id} className="card card-pad stack" style={{ gap: 10 }}>
              <div>
                <h3>{family.name}</h3>
                <p className="muted small">
                  {family.member_count} üye · {family.role === "admin" ? "Yönetici" : "Üye"}
                </p>
              </div>
              <div className="row">
                <Link className="btn btn-sm btn-primary" to={{ pathname: "/plan", search: `?aile=${family.family_id}` }}>
                  Aile planı
                </Link>
                <Link className="btn btn-sm" to={`/aile/${family.family_id}`}>
                  Üyeler ve davet
                </Link>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="card card-pad" aria-label="Yeni aile">
        <form className="form" onSubmit={submit} noValidate>
          <h2>Yeni aile oluştur</h2>
          <div className="field">
            <label htmlFor="family-name">Aile adı</label>
            <input
              id="family-name"
              className="input"
              placeholder="Örn. Yılmaz Ailesi"
              value={name}
              maxLength={100}
              onChange={(event) => setName(event.target.value)}
            />
          </div>
          {create.error && <ErrorNote error={create.error} />}
          <div>
            <button type="submit" className="btn btn-primary" disabled={create.isPending || !name.trim()}>
              {create.isPending ? "Oluşturuluyor…" : "Aile oluştur"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
