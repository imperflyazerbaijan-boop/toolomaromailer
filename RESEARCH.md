# Research checkpoint — 2026-11-26
## Verified source findings
- Google AdSense earnings depend on visitor location, traffic, content and ad setup: https://support.google.com/adsense/answer/9902?hl=en
- RPM is an estimate per thousand impressions, not a universal country tariff: https://support.google.com/adsense/answer/190515?hl=en
- IAB Europe 2025 AdEx reports EUR 131bn digital ad investment across the European market, published July 7 2026: https://iabeurope.eu/iab-europes-adex-benchmark-2025-report/
- Google Places includes websiteUri but not a business email field: https://developers.google.com/maps/documentation/places/web-service/reference/rest/v1/places
- Google Maps content scraping and external export/storage are restricted: https://developers.google.com/maps/documentation/places/web-service/policies
- UK ICO B2B marketing guidance: https://ico.org.uk/for-organisations/direct-marketing-and-privacy-and-electronic-communications/business-to-business-marketing/
- Germany UWG section 7 generally requires prior express consent for email advertising, subject to statutory exceptions: https://www.gesetze-im-internet.de/uwg_2004/__7.html
## Country shortlist
countries.txt includes 40 candidate markets (including Hong Kong and Taiwan as geographic markets). It is not verified country-by-country RPM data. Prioritize using actual Toolomaro AdSense country reports when available.
## Archive audit
Music.rar contained 10,351 archive entries across str (1,514), transport geniş (2,206), transport_scraper_ideal (2,195), fachkraft_18b_scraper_ideal (2,218), sprinter (2,218). Inspected code in str/core/state.py, str/core/http_client.py, str/core/exporter.py, str/supervisor.py. Existing concepts include WAL, locking, status records, cooldowns and restart supervision; old exporter creates three sheets, incompatible with new one-sheet requirement. No old scraping or anti-block logic copied. Only four files inspected; not a full archive audit.
## Outstanding
No live country-specific platform HTML or API audit or permitted source integration completed. Candidate directories from the initial chat are not validated for data access or email fields. Need actual authorized source exports before testing ingestion on real data.
