# Supabase setup (once, ~5 minutes)

1. **Create a project** at https://supabase.com (free tier is enough). Any region; pick one close to Mexico, such as East US.
2. **Create the table:** SQL Editor → New query → paste [`schema.sql`](schema.sql) → Run.
3. **Allow the site to sign in:** Authentication → URL Configuration
   - Site URL: `https://mattyinc.github.io/dayline/` (a reused project is often still on the default `http://localhost:3000`, which sends sign-in links to the wrong place)
   - Redirect URLs: add `https://mattyinc.github.io/dayline/` and `http://localhost:5178/`
4. **Show the 6-digit code in the email** (so you can read it on your phone and type it on the work laptop):
   Authentication → Emails → Templates → add `{{ .Token }}` to **both** *Confirm signup* (used on your very first sign-in) and *Magic Link* (every sign-in after that), for example:
   `<p>Your Dayline code: <strong>{{ .Token }}</strong></p>`
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
