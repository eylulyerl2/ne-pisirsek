import { useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ConfirmButton } from "../components/ConfirmButton";
import { CopyButton } from "../components/CopyButton";
import { ErrorNote, Spinner } from "../components/Feedback";
import { ShareCard } from "../components/ShareCard";
import {
  useCancelPasswordReset,
  useCreateInvitation,
  useCreatePasswordReset,
  useDeleteFamily,
  useFamily,
  useFamilyInvitations,
  useRegenerateInvitation,
  useRemoveMember,
  useRenameFamily,
  useRevokeInvitation,
  useSetMemberRole,
} from "../hooks/queries";
import { useAuth } from "../hooks/useAuth";
import type { FamilyMember, Invitation } from "../services/types";
import { formatDayMonth } from "../utils/dates";
import { inviteLink, inviteMessage, resetLink, resetMessage } from "../utils/nav";

function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toLocaleUpperCase("tr-TR"))
    .join("");
}

export function FamilyDetailPage() {
  const { familyId = "" } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const family = useFamily(familyId);
  const isAdmin = family.data?.role === "admin";
  const isFounder = !!family.data && family.data.created_by === user?.user_id;
  const invitations = useFamilyInvitations(familyId, isAdmin);

  const rename = useRenameFamily(familyId);
  const remove = useDeleteFamily(familyId);
  const setRole = useSetMemberRole(familyId);
  const removeMember = useRemoveMember(familyId);
  const createInvitation = useCreateInvitation(familyId);
  const regenerate = useRegenerateInvitation(familyId);
  const revoke = useRevokeInvitation(familyId);
  const createReset = useCreatePasswordReset(familyId);
  const cancelReset = useCancelPasswordReset(familyId);

  const [editing, setEditing] = useState(false);
  const [newName, setNewName] = useState("");
  const [label, setLabel] = useState("");
  const [fresh, setFresh] = useState<Invitation | null>(null);
  const [reset, setReset] = useState<{ name: string; token: string; code: string } | null>(null);

  if (family.isPending) return <Spinner />;
  if (family.isError) {
    return (
      <div className="stack">
        <ErrorNote error={family.error} />
        <div>
          <Link className="btn" to="/aile">
            Ailelerime dön
          </Link>
        </div>
      </div>
    );
  }
  const data = family.data;
  const failure = rename.error ?? remove.error ?? setRole.error ?? removeMember.error ?? createReset.error ?? cancelReset.error;
  const inviteFailure = createInvitation.error ?? regenerate.error ?? revoke.error;

  function submitRename(event: FormEvent) {
    event.preventDefault();
    rename.mutate(newName, { onSuccess: () => setEditing(false) });
  }

  function submitInvitation(event: FormEvent) {
    event.preventDefault();
    createInvitation.mutate(label.trim() || undefined, {
      onSuccess: (invitation) => {
        setFresh(invitation);
        setLabel("");
      },
    });
  }

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          {editing ? (
            <form className="row" onSubmit={submitRename} noValidate>
              <label htmlFor="rename" className="visually-hidden">
                Aile adı
              </label>
              <input id="rename" className="input" style={{ width: 260 }} value={newName} maxLength={100} onChange={(e) => setNewName(e.target.value)} autoFocus />
              <button type="submit" className="btn btn-primary btn-sm" disabled={rename.isPending || !newName.trim()}>
                Kaydet
              </button>
              <button type="button" className="btn btn-sm" onClick={() => setEditing(false)}>
                Vazgeç
              </button>
            </form>
          ) : (
            <div className="row">
              <h1>{data.name}</h1>
              {isAdmin && (
                <button
                  type="button"
                  className="btn btn-sm btn-ghost"
                  onClick={() => {
                    setNewName(data.name);
                    setEditing(true);
                  }}
                >
                  Adı değiştir
                </button>
              )}
            </div>
          )}
          <p>
            {data.member_count} üye · Siz {isAdmin ? "yöneticisiniz" : "üyesiniz"}
          </p>
        </div>
        <Link className="btn btn-primary" to={{ pathname: "/plan", search: `?aile=${data.family_id}` }}>
          Aile planını aç
        </Link>
      </div>

      {failure && <ErrorNote error={failure} />}

      <section className="card" aria-labelledby="members-title">
        <h2 id="members-title" style={{ padding: "16px 16px 8px" }}>
          Üyeler
        </h2>
        <ul className="member-list">
          {data.members.map((member) => (
            <MemberRow
              key={member.user_id}
              member={member}
              isSelf={member.user_id === user?.user_id}
              isFounder={member.user_id === data.created_by}
              canManage={isAdmin}
              busy={setRole.isPending || removeMember.isPending}
              resetBusy={createReset.isPending || cancelReset.isPending}
              onReset={() =>
                createReset.mutate(member.user_id, {
                  onSuccess: (result) => setReset({ name: result.member_name, token: result.token, code: result.code }),
                })
              }
              onCancelReset={() =>
                cancelReset.mutate(member.user_id, {
                  onSuccess: () => setReset((current) => (current?.name === member.full_name ? null : current)),
                })
              }
              onRole={(role) => setRole.mutate({ userId: member.user_id, role })}
              onRemove={() => removeMember.mutate(member.user_id)}
              onLeave={() => removeMember.mutate(member.user_id, { onSuccess: () => navigate("/aile") })}
            />
          ))}
        </ul>
      </section>

      {reset && (
        <ShareCard
          title={`${reset.name} için şifre sıfırlama bağlantısı hazır`}
          link={resetLink(reset.token)}
          code={reset.code}
          message={resetMessage(reset.token, reset.code)}
          note="Bağlantı ve şifre 24 saat geçerli, yalnızca bir kez kullanılabilir. Kişi bağlantıyı açıp bu şifreyle kendi yeni şifresini belirler; o zamana kadar eski şifresi geçerli kalır. Şifreyi bağlantıdan ayrı bir yolla (yüz yüze ya da telefonla) iletmeniz daha güvenli olur."
        />
      )}

      {isAdmin && (
        <section className="card card-pad stack" aria-labelledby="invite-title">
          <div>
            <h2 id="invite-title">Aileye üye ekle</h2>
            <p className="muted small">
              E-posta adresi olmayan çocuklar ve büyükler de katılabilir. Bir bağlantı ve <strong>tek kullanımlık şifre</strong> oluşturun, ikisini de katılacak kişiye iletin. Kişi bağlantıyı açıp şifreyi girerek kendi hesabını oluşturur. Davet 7 gün geçerli.
            </p>
          </div>
          <form className="row" onSubmit={submitInvitation} noValidate>
            <div className="field" style={{ flex: 1, minWidth: 220 }}>
              <label htmlFor="invite-label">Kimin için? (isteğe bağlı)</label>
              <input id="invite-label" className="input" placeholder="Örn. Elif" maxLength={100} value={label} onChange={(e) => setLabel(e.target.value)} />
            </div>
            <button type="submit" className="btn btn-primary" disabled={createInvitation.isPending} style={{ alignSelf: "flex-end" }}>
              Bağlantı ve şifre oluştur
            </button>
          </form>
          {inviteFailure && <ErrorNote error={inviteFailure} />}

          {fresh?.code && (
            <ShareCard
              title={fresh.label ? `${fresh.label} için davet hazır` : "Davet hazır"}
              link={inviteLink(fresh.token)}
              code={fresh.code}
              message={inviteMessage(data.name, fresh.token, fresh.code)}
              note="Şifre yalnızca şimdi görünür ve bir kez kullanılabilir. Kaybederseniz aşağıdan &quot;Yeni şifre üret&quot; ile yenileyebilirsiniz. Şifreyi bağlantıdan ayrı bir yolla iletmeniz daha güvenli olur."
            />
          )}

          {invitations.data && invitations.data.length > 0 && (
            <div>
              <h3 style={{ marginBottom: 8 }}>Bekleyen davetler</h3>
              <ul className="member-list" style={{ margin: 0 }}>
                {invitations.data.map((item) => (
                  <li key={item.invitation_id} className="member-row">
                    <div className="grow">
                      <strong>{item.label ?? "İsimsiz davet"}</strong>
                      <span className="muted small" style={{ display: "block" }}>
                        {item.status === "locked" ? (
                          <span className="lock-note">Kilitli: çok fazla yanlış şifre denendi · </span>
                        ) : item.failed_attempts > 0 ? (
                          `${item.failed_attempts} yanlış deneme · `
                        ) : null}
                        {formatDayMonth(new Date(item.expires_at))} tarihine kadar geçerli
                      </span>
                    </div>
                    <CopyButton text={inviteLink(item.token)} label="Bağlantıyı kopyala" />
                    <button
                      type="button"
                      className="btn btn-sm"
                      disabled={regenerate.isPending}
                      onClick={() => regenerate.mutate(item.invitation_id, { onSuccess: setFresh })}
                    >
                      Yeni şifre üret
                    </button>
                    <button type="button" className="btn btn-sm btn-danger" disabled={revoke.isPending} onClick={() => revoke.mutate(item.invitation_id)}>
                      İptal et
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}

      {isFounder && (
        <section className="card card-pad stack danger-zone" aria-labelledby="danger-title">
          <h2 id="danger-title">Tehlikeli bölge</h2>
          <p className="muted small">Aile silinince ailenin tüm haftalık planları ve alışveriş listeleri de silinir. Bu işlemi yalnızca aileyi kuran kişi yapabilir.</p>
          <div>
            <ConfirmButton
              confirmText="Aile ve tüm planları silinsin mi?"
              confirmLabel="Evet, ailemi sil"
              disabled={remove.isPending}
              onConfirm={() => remove.mutate(undefined, { onSuccess: () => navigate("/aile") })}
            >
              Aileyi sil
            </ConfirmButton>
          </div>
        </section>
      )}
    </div>
  );
}

interface MemberRowProps {
  member: FamilyMember;
  isSelf: boolean;
  isFounder: boolean;
  canManage: boolean;
  busy: boolean;
  resetBusy: boolean;
  onRole: (role: "admin" | "member") => void;
  onRemove: () => void;
  onLeave: () => void;
  onReset: () => void;
  onCancelReset: () => void;
}

function MemberRow({ member, isSelf, isFounder, canManage, busy, resetBusy, onRole, onRemove, onLeave, onReset, onCancelReset }: MemberRowProps) {
  return (
    <li className="member-row">
      <span className="avatar" aria-hidden="true">
        {initials(member.full_name)}
      </span>
      <div className="grow">
        <strong>
          {member.full_name}
          {isSelf && <span className="muted small"> (siz)</span>}
        </strong>
        <span className="muted small" style={{ display: "block" }}>
          {isFounder ? "Kurucu" : member.role === "admin" ? "Yönetici" : "Üye"}
          {member.username ? ` · @${member.username}` : ""}
          {member.joined_at ? ` · ${formatDayMonth(new Date(member.joined_at))} tarihinde katıldı` : ""}
          {member.reset_pending && <span className="lock-note"> · Şifre sıfırlama bekliyor</span>}
        </span>
      </div>
      <div className="row" style={{ justifyContent: "flex-end" }}>
        {member.can_reset_password && (
          <button type="button" className="btn btn-sm" disabled={resetBusy} onClick={onReset}>
            {member.reset_pending ? "Yeni sıfırlama bağlantısı" : "Şifre sıfırla"}
          </button>
        )}
        {member.can_reset_password && member.reset_pending && (
          <button type="button" className="btn btn-sm btn-danger" disabled={resetBusy} onClick={onCancelReset}>
            Sıfırlamayı iptal et
          </button>
        )}
        {canManage && (
          <button type="button" className="btn btn-sm" disabled={busy} onClick={() => onRole(member.role === "admin" ? "member" : "admin")}>
            {member.role === "admin" ? "Üyeliğe düşür" : "Yönetici yap"}
          </button>
        )}
        {isSelf ? (
          <ConfirmButton confirmText="Aileden ayrılmak istiyor musunuz?" confirmLabel="Evet, ayrıl" disabled={busy} onConfirm={onLeave}>
            Aileden ayrıl
          </ConfirmButton>
        ) : (
          canManage && (
            <ConfirmButton confirmText={`${member.full_name} çıkarılsın mı?`} confirmLabel="Evet, çıkar" disabled={busy} onConfirm={onRemove}>
              Çıkar
            </ConfirmButton>
          )
        )}
      </div>
    </li>
  );
}
