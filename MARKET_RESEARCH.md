# Market research — 2026-11-26
Google's Countries report measures this publisher's actual performance by visitor country; earnings depend on content, users and advertising configuration. Page RPM = estimated earnings / pageviews * 1000. Sources: https://support.google.com/adsense/answer/9974594 and https://support.google.com/adsense/answer/9902 and https://support.google.com/adsense/answer/190515.
## 2025 proxy (not AdSense RPM)
Digital 2026 Global Overview Report (Kepios / Statista Market Insights, October 2025, p. 637) estimates annual digital ad expenditure per internet user in USD. It provides data for 30 of the 40 configured markets. See https://datareportal.com/reports/digital-2026-global-overview-report and https://wearesocial.com/wp-content/uploads/2025/10/GDR-2026.pdf. The chart's indexed text was available; visual PDF verification failed due to server file-size limits. Numbers are estimates, not publisher income or a 2026 forecast.

| Country | 2025 proxy USD |
|---|---:|
| United States | 1078 |
| United Kingdom | 763 |
| Australia | 586 |
| Switzerland | 538 |
| Sweden | 520 |
| Norway | 514 |
| Canada | 485 |
| Denmark | 408 |
| New Zealand | 395 |
| Singapore | 370 |
| Hong Kong | 340 |
| Netherlands | 338 |
| Japan | 303 |
| Ireland | 271 |
| Austria | 269 |
| South Korea | 256 |
| France | 218 |
| Finland | 216 |
| Germany | 211 |
| Taiwan | 200 |
| Israel | 199 |
| Czechia | 184 |
| Belgium | 153 |
| Spain | 142 |
| Italy | 140 |
| Portugal | 125 |
| United Arab Emirates | 119 |
| Greece | 113 |
| Poland | 74.18 |
| Saudi Arabia | 64.69 |
Missing comparable values in this chart: Bahrain, Cyprus, Estonia, Iceland, Kuwait, Lithuania, Luxembourg, Malta, Qatar, Slovenia. Do not assign invented values. WARC's 2025 ad market forecast independently identifies the US as largest by total spending and the UK as the largest European market, but that metric differs from per-user spending: https://www.warc.com/en/press/press-releases/25-12-11_global-ad-market-prospects-upgraded-to-8-but-growth-concentrated-in-Big-Tech-platforms

## Source feasibility
- Mailchimp Marketing API: implemented for user-owned permission-based audiences, not business discovery. List member endpoint supports count/offset, subscription status, merge fields and marketing permissions. https://mailchimp.com/developer/marketing/api/lists/members/list-members ; limit 10 simultaneous connections per user: https://mailchimp.com/developer/marketing/api-concepts/rate-limits-and-timeouts/ ; scraping third-party lists is disallowed: https://mailchimp.com/help/requirements-best-practices-audiences/
- GLEIF API: international legal-entity lookup for entities with LEIs, legal name and registered address. Useful to identify companies but not a marketing email database. Coverage is not equivalent to all companies. https://www.gleif.org/en/lei-data/gleif-api and https://www.gleif.org/en/lei-data/access-and-use-lei-data/level-1-data-who-is-who
- European BRIS: searches connected official business registries, not an authorized bulk marketing contact source. https://e-justice.europa.eu/topics/registers-business-insolvency-land/business-registers-search-company-eu/general-information-find-company_en
- OpenCorporates: company name, jurisdiction, registration details; API access and licensing must be checked for commercial use. https://api.opencorporates.com/documentation/API-Reference and https://opencorporates.com/legal-information/self-service-api-terms-of-service/
No live site-level directory audit or 40-country list of email providers was completed. Public listing access does not establish permission to harvest or contact. No real user-owned source credentials available.
