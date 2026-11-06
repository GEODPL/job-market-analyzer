-- Τρέξε το μία φορά στο Supabase: SQL Editor -> New query -> Run

create table if not exists app_users (
  username      text primary key,
  password_hash text not null,
  salt          text not null,
  created_at    timestamptz not null default now()
);

-- Κλείδωμα: με RLS ενεργό και χωρίς policies, το public (anon) key ΔΕΝ έχει καμία πρόσβαση.
-- Μόνο το service_role key (που ζει στα Secrets του server) μπορεί να διαβάσει/γράψει.
alter table app_users enable row level security;
