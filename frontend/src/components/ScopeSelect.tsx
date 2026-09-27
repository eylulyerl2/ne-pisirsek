import { Link } from "react-router-dom";
import { useFamilies } from "../hooks/queries";

interface ScopeSelectProps {
  familyId: string | null;
  onChange: (familyId: string | null) => void;
}

/** Planın kime ait olduğunu seçer: kişisel plan ya da üyesi olunan aileler. */
export function ScopeSelect({ familyId, onChange }: ScopeSelectProps) {
  const families = useFamilies();

  if (families.data && families.data.length === 0) {
    return (
      <p className="muted small">
        Aileniz için de menü planlamak ister misiniz? <Link to="/aile">Aile oluşturun veya davet kabul edin.</Link>
      </p>
    );
  }
  if (!families.data) return null;

  return (
    <div className="field" style={{ maxWidth: 320 }}>
      <label htmlFor="scope">Kimin için planlıyorsunuz?</label>
      <select id="scope" className="select" value={familyId ?? ""} onChange={(event) => onChange(event.target.value || null)}>
        <option value="">Kişisel plan</option>
        {families.data.map((family) => (
          <option key={family.family_id} value={family.family_id}>
            {family.name} ({family.member_count} kişi)
          </option>
        ))}
      </select>
    </div>
  );
}
