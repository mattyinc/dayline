# Supabase setup (once, ~5 minutes)

1. **Create a project** at https://supabase.com (free tier is enough). Any region; pick one close to Mexico, such as East US.
2. **Create the table:** SQL Editor → New query → paste [`schema.sql`](schema.sql) → Run.
3. **Allow the site to sign in:** Authentication → URL Configuration → Redirect URLs → add
   `https://mattyinc.github.io/dayline/**` and `http://localhost:5178/**`.
   The `/**` matters: without it, `.../dayline/` doesn't match and links fall back to the Site URL (often `http://localhost:3000`).
   Leave the Site URL alone if another app uses this project.
4. **Sign-in works like this** (the free plan doesn't allow editing email templates, so there's no 6-digit code):
   - First machine: Dayline → Assistant → *First time? Email me a link* → open the link **in the same browser**.
   - Still there: type a password under *Password for your other machines* → *Set password*.
   - Every other machine: email + password → *Sign in*.
   - The built-in email service only sends a few emails per hour; if one doesn't arrive, wait.
5. **Copy the keys:** Project Settings → API → *Project URL* and the *anon public* key.
   Paste them into `SUPABASE_CONFIG` near the sync section in `index.html` and push, so every machine is pre-configured.
   (Or paste them into the Assistant view on each machine instead.)
   Never use the `service_role` key here.
6. **Open the site and sign in** with your email. Then **lock it down:**
   Authentication → Sign In / Providers → turn off *Allow new users to sign up*. Only your account can use the database after that.

## Notes
- The anon key is meant to be public. Row-level security in `schema.sql` is what keeps rows private.
- Free projects pause after about a week with no activity; open the dashboard and click *Restore* if that happens.
- Don't put client data (customer names, account numbers, extracts) in item titles or notes. This database lives outside your work machines.
