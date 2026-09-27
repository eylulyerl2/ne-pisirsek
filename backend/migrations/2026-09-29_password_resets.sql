-- Şifre sıfırlama bağlantısı: aile yöneticisi, ailenin açtığı hesaplar için bağlantı + tek kullanımlık şifre üretir.

-- Hesabı hangi ailenin açtığı (davetle katılırken doldurulur); yönetici yalnızca bu hesapların şifresini sıfırlayabilir
ALTER TABLE profiles
    ADD COLUMN created_via_family_id UUID,
    ADD CONSTRAINT fk_profiles_created_via_family FOREIGN KEY (created_via_family_id) REFERENCES families (family_id) ON DELETE SET NULL;

CREATE TABLE password_resets (
    reset_id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES profiles (user_id) ON DELETE CASCADE,
    created_by UUID REFERENCES profiles (user_id) ON DELETE SET NULL,
    token VARCHAR(64) NOT NULL UNIQUE,
    code_hash VARCHAR(255) NOT NULL,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    used_at TIMESTAMPTZ,
    CONSTRAINT ck_password_resets_status CHECK (status IN ('pending', 'used', 'locked', 'expired'))
);
CREATE INDEX ix_password_resets_user_id ON password_resets (user_id);
