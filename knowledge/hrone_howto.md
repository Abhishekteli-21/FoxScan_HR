# HROne — How-To Guides

> This file holds step-by-step guides for using the HROne platform (apply leave, mark
> attendance, download payslips, raise helpdesk tickets, …).
>
> **Status: placeholder.** The help portal is unreachable from cloud sandboxes, so the
> crawl has to run on a machine inside a normal network and travel back through git:
>
> ```bash
> pip install requests beautifulsoup4
> python scripts/crawl_help_portal.py          # → knowledge/hrone_howto_crawled.md
> git add knowledge/hrone_howto_crawled.md && git commit -m "Add crawled HROne articles"
> git push
> ```
>
> The curated articles then get merged into this file. HR can equally well paste their
> own step-by-step instructions below — either source works.
>
> Until real steps are added, the assistant will say what CAN be done in HROne and point
> employees to the official help portal rather than inventing UI steps.

## Where to do things in HROne (general pointers)

- HROne is available as a web portal and a mobile app (Android/iOS).
- Typical employee self-service actions in HROne include: applying for leave, checking
  leave balance, marking/regularizing attendance, downloading payslips and letters,
  submitting expense claims, and raising HR helpdesk tickets.
- Official employee help articles: https://employee-help.hrone.cloud/
- If an employee cannot log in to HROne, they should contact HR to verify their
  employee code and registered email/mobile number.

<!-- CRAWLED / CURATED ARTICLES GO BELOW THIS LINE -->
