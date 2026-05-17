
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "pgcrypto";


-- ─── Users ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    phone       VARCHAR(20) UNIQUE NOT NULL,
    name        VARCHAR(100),
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone);


-- ─── Doctors ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS doctors (
    id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    specialty   VARCHAR(100) NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);


-- ─── Slots ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS slots (
    id            UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    doctor_id     UUID REFERENCES doctors(id) ON DELETE CASCADE,
    date          DATE NOT NULL,
    time_slot     TIME NOT NULL,
    is_available  BOOLEAN DEFAULT TRUE,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(doctor_id, date, time_slot)   -- prevents double-booking at DB level
);

CREATE INDEX IF NOT EXISTS idx_slots_available ON slots(is_available, date);
CREATE INDEX IF NOT EXISTS idx_slots_doctor    ON slots(doctor_id);


-- ─── Appointments ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS appointments (
    id           UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id      UUID REFERENCES users(id) ON DELETE CASCADE,
    slot_id      UUID REFERENCES slots(id),
    doctor_name  VARCHAR(100) NOT NULL,
    specialty    VARCHAR(100) NOT NULL,
    date         DATE NOT NULL,
    time_slot    TIME NOT NULL,
    status       VARCHAR(20) DEFAULT 'booked'
                     CHECK (status IN ('booked', 'cancelled', 'completed')),
    notes        TEXT,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_appointments_user   ON appointments(user_id);
CREATE INDEX IF NOT EXISTS idx_appointments_status ON appointments(status);


-- ─── Call Sessions ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS call_sessions (
    id                  UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id          VARCHAR(100) UNIQUE NOT NULL,
    user_id             UUID REFERENCES users(id),
    transcript          JSONB DEFAULT '[]',
    summary             TEXT,
    appointments_made   JSONB DEFAULT '[]',
    user_preferences    JSONB DEFAULT '{}',
    started_at          TIMESTAMPTZ DEFAULT NOW(),
    ended_at            TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON call_sessions(user_id);


-- ─── Seed Data: Doctors ───────────────────────────────────
INSERT INTO doctors (id, name, specialty) VALUES
    ('d1000000-0000-0000-0000-000000000001', 'Dr. Ananya Sharma',    'Cardiology'),
    ('d1000000-0000-0000-0000-000000000002', 'Dr. Rohan Mehta',      'Dermatology'),
    ('d1000000-0000-0000-0000-000000000003', 'Dr. Priya Nair',       'General Physician'),
    ('d1000000-0000-0000-0000-000000000004', 'Dr. Vikram Patel',     'Orthopedics'),
    ('d1000000-0000-0000-0000-000000000005', 'Dr. Sunita Krishnan',  'Gynecology')
ON CONFLICT DO NOTHING;


-- ─── Seed Data: Slots (next 7 days) ──────────────────────
-- Generates slots for each doctor: 9am, 10am, 11am, 2pm, 3pm
-- You can run this seed or replace with dynamic generation.

DO $$
DECLARE
    doc_id  UUID;
    d       DATE;
    t       TIME;
    doc_ids UUID[] := ARRAY[
        'd1000000-0000-0000-0000-000000000001',
        'd1000000-0000-0000-0000-000000000002',
        'd1000000-0000-0000-0000-000000000003',
        'd1000000-0000-0000-0000-000000000004',
        'd1000000-0000-0000-0000-000000000005'
    ];
    times   TIME[] := ARRAY['09:00', '10:00', '11:00', '14:00', '15:00'];
BEGIN
    FOREACH doc_id IN ARRAY doc_ids LOOP
        FOR i IN 0..6 LOOP
            d := CURRENT_DATE + i;
            FOREACH t IN ARRAY times LOOP
                INSERT INTO slots (doctor_id, date, time_slot, is_available)
                VALUES (doc_id, d, t, TRUE)
                ON CONFLICT DO NOTHING;
            END LOOP;
        END LOOP;
    END LOOP;
END $$;


-- ─── Seed Data: Users ─────────────────────────────────────
INSERT INTO users (id, phone, name) VALUES
    ('a1000000-0000-0000-0000-000000000001', '+919988776655', 'Rajesh Kumar'),
    ('a1000000-0000-0000-0000-000000000002', '+918877665544', 'Sita Williams'),
    ('a1000000-0000-0000-0000-000000000003', '+917766554433', 'Amitabh Singh')
ON CONFLICT (phone) DO NOTHING;


-- ─── Seed Data: Appointments ──────────────────────────────
-- Assigning some sample appointments to Rajesh Kumar
INSERT INTO appointments (user_id, slot_id, doctor_name, specialty, date, time_slot, status, notes)
SELECT 
    'a1000000-0000-0000-0000-000000000001',
    s.id,
    d.name,
    d.specialty,
    s.date,
    s.time_slot,
    'booked',
    'Follow-up for routine checkup'
FROM slots s
JOIN doctors d ON s.doctor_id = d.id
WHERE d.name = 'Dr. Ananya Sharma' 
AND s.date = CURRENT_DATE + 1
AND s.time_slot = '10:00:00'
LIMIT 1
ON CONFLICT DO NOTHING;

-- Mark the slot as unavailable
UPDATE slots SET is_available = FALSE 
WHERE id IN (SELECT slot_id FROM appointments WHERE user_id = 'a1000000-0000-0000-0000-000000000001');


-- ─── Seed Data: Call Sessions ─────────────────────────────
INSERT INTO call_sessions (session_id, user_id, transcript, summary, appointments_made) VALUES
    (
        'sess_test_001', 
        'a1000000-0000-0000-0000-000000000001', 
        '[{"role": "agent", "text": "Hello Rajesh, how can I help you today?"}, {"role": "user", "text": "I want to book an appointment with Dr. Ananya."}]',
        'User booked an appointment with Dr. Ananya Sharma for tomorrow at 10 AM.',
        '[{"doctor": "Dr. Ananya Sharma", "time": "10:00 AM", "date": "Tomorrow"}]'
    )
ON CONFLICT (session_id) DO NOTHING;
