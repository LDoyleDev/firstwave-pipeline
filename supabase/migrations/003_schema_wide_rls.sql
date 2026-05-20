-- Run this in the Supabase SQL editor. Idempotent — safe to re-run.
-- Schema-wide Row Level Security pass. Pairs with the Supabase Auth swap on the
-- frontend (PasswordGate -> AuthGate): the dashboard now logs in for real, so the
-- browser acts as the `authenticated` role instead of the bare `anon` key.
--
-- Access model after this migration:
--   service_role (backend)            -> bypasses RLS entirely. Unchanged.
--   authenticated (logged-in operator)-> SELECT only, on the 5 tables the dashboard reads.
--   anon (public key in the JS bundle)-> NO access to any table.
--
-- Writes for every table go through the service-role backend. No write policy
-- exists for anon/authenticated, so RLS default-deny blocks all INSERT/UPDATE/
-- DELETE from the browser — this is intentional, not an omission.
--
-- WARNING: running this is the moment the anon key loses read access. Deploy the
-- frontend AuthGate build and create the operator auth user FIRST (see WORK_LOG).

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. Enable RLS on every table that is currently unprotected.
--    suppression_list already had RLS enabled in 002_compliance_layer.sql.
-- ---------------------------------------------------------------------------
ALTER TABLE companies        ENABLE ROW LEVEL SECURITY;
ALTER TABLE leads            ENABLE ROW LEVEL SECURITY;
ALTER TABLE investor_targets ENABLE ROW LEVEL SECURITY;
ALTER TABLE meetings         ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_sequences  ENABLE ROW LEVEL SECURITY;
ALTER TABLE voice_commands   ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_config    ENABLE ROW LEVEL SECURITY;

-- ---------------------------------------------------------------------------
-- 2. Read access for the logged-in operator (role: authenticated).
--    The dashboard reads exactly these five tables via the Supabase JS client
--    (leads, investor_targets, meetings, voice_commands, email_sequences) and
--    holds realtime subscriptions on the first three. USING (true) = every row;
--    this is a single-operator tool, not multi-tenant.
--    DROP-then-CREATE keeps the migration re-runnable (policies have no IF NOT EXISTS).
-- ---------------------------------------------------------------------------
DROP POLICY IF EXISTS authenticated_read ON leads;
CREATE POLICY authenticated_read ON leads
  FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS authenticated_read ON investor_targets;
CREATE POLICY authenticated_read ON investor_targets
  FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS authenticated_read ON meetings;
CREATE POLICY authenticated_read ON meetings
  FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS authenticated_read ON voice_commands;
CREATE POLICY authenticated_read ON voice_commands
  FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS authenticated_read ON email_sequences;
CREATE POLICY authenticated_read ON email_sequences
  FOR SELECT TO authenticated USING (true);

-- Explicit table grant so the migration does not silently depend on Supabase's
-- default privileges. SELECT only — the RLS policy above scopes it to reads.
GRANT SELECT ON leads, investor_targets, meetings, voice_commands, email_sequences
  TO authenticated;

-- ---------------------------------------------------------------------------
-- 3. Lock the anon key out of everything.
--    The anon key ships inside the browser bundle and is effectively public.
--    RLS with no anon policy already denies it; REVOKE is the second lock — a
--    policy still needs a table grant to take effect, so a future mis-added
--    anon policy cannot leak data on its own.
-- ---------------------------------------------------------------------------
REVOKE ALL ON companies, leads, investor_targets, meetings,
              email_sequences, voice_commands, system_config
  FROM anon;

-- companies and system_config are backend-only — only the service-role key
-- ever reads them. Lock authenticated out of these two as well.
REVOKE ALL ON companies, system_config FROM authenticated;

COMMIT;

-- Verify after running:
--   SELECT relname, relrowsecurity FROM pg_class
--    WHERE relname IN ('companies','leads','investor_targets','meetings',
--                      'email_sequences','voice_commands','system_config',
--                      'suppression_list');
--   -- relrowsecurity expect TRUE for all 8
--
--   SELECT tablename, policyname, roles, cmd FROM pg_policies
--    WHERE schemaname = 'public' ORDER BY tablename;
--   -- expect exactly one SELECT policy for {authenticated} on each of:
--   -- leads, investor_targets, meetings, voice_commands, email_sequences
--
--   SELECT grantee, privilege_type FROM information_schema.role_table_grants
--    WHERE table_name = 'leads' AND grantee IN ('anon','authenticated');
--   -- expect anon: no rows; authenticated: SELECT only
