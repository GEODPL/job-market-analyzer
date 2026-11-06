-- Πίνακας αγγελιών που γεμίζει το scraper.py. Τρέξε το μία φορά στο Supabase: SQL Editor -> New query -> Run
-- Οι στήλες αντιστοιχούν στα πεδία που γράφει το scraper.py.

create table if not exists job_postings (
  job_id          text primary key,
  title           text,
  company         text,
  description     text,
  url             text,
  posted_at       text,
  category        text,
  location        text,
  employment_type text,
  remote          text,
  seniority       text,
  salary_min      numeric,
  salary_max      numeric,
  salary_currency text
);

-- Η εφαρμογή (Streamlit) διαβάζει με το publishable (anon) key, οπότε χρειάζεται policy ανάγνωσης.
-- Το scraper γράφει με το secret (service_role) key, που παρακάμπτει το RLS.
alter table job_postings enable row level security;

drop policy if exists "public read job_postings" on job_postings;
create policy "public read job_postings" on job_postings for select using (true);
