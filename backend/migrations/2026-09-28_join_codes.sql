-- Aile daveti: e-posta yerine bağlantı + tek kullanımlık şifre; e-postasız (kullanıcı adlı) hesaplar.
-- Alembic kurulana kadar geçişler elle uygulanır (sırasıyla, tek işlemde).

-- 1) Hesaplar: e-posta artık zorunlu değil, kullanıcı adı eklendi (en az biri şart)
ALTER TABLE profiles ALTER COLUMN email DROP NOT NULL;
ALTER TABLE profiles ADD COLUMN username VARCHAR(30);
CREATE UNIQUE INDEX ix_profiles_username ON profiles (username);
ALTER TABLE profiles ADD CONSTRAINT ck_profiles_login_identifier CHECK (email IS NOT NULL OR username IS NOT NULL);

-- 2) Davetler: eski e-posta tabanlı davetler kullanılamaz hale geldiği için silinir
DELETE FROM family_invitations;
ALTER TABLE family_invitations DROP COLUMN invited_email;
ALTER TABLE family_invitations
    ADD COLUMN label VARCHAR(100),
    ADD COLUMN code_hash VARCHAR(255) NOT NULL,
    ADD COLUMN failed_attempts INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN used_by UUID REFERENCES profiles (user_id) ON DELETE SET NULL,
    ADD COLUMN used_at TIMESTAMPTZ;
ALTER TABLE family_invitations DROP CONSTRAINT ck_family_invitations_status;
ALTER TABLE family_invitations
    ADD CONSTRAINT ck_family_invitations_status CHECK (status IN ('pending', 'accepted', 'expired', 'locked'));
