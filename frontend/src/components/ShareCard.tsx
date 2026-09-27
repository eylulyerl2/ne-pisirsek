import { formatCode } from "../utils/nav";
import { CopyButton } from "./CopyButton";

interface ShareCardProps {
  title: string;
  link: string;
  code: string;
  /** Panoya kopyalanacak hazır mesaj (bağlantı + şifre). */
  message: string;
  note: string;
}

/** Bağlantı ve tek kullanımlık şifreyi bir kez gösteren kart (davet ve şifre sıfırlama için ortak). */
export function ShareCard({ title, link, code, message, note }: ShareCardProps) {
  return (
    <div className="banner banner-info invite-result" role="status">
      <div className="grow stack" style={{ gap: 10 }}>
        <strong>{title}</strong>
        <div>
          <span className="small">Bağlantı</span>
          <div className="invite-link">{link}</div>
        </div>
        <div>
          <span className="small">Tek kullanımlık şifre</span>
          <div className="invite-code" aria-label="Tek kullanımlık şifre">
            {formatCode(code)}
          </div>
        </div>
        <div className="row">
          <CopyButton primary text={message} label="Bağlantı ve şifreyi kopyala" />
          <CopyButton text={link} label="Yalnızca bağlantıyı kopyala" />
        </div>
        <p className="small">{note}</p>
      </div>
    </div>
  );
}
