"""Read-only adapter for a user-owned Mailchimp audience with explicit permission."""
import os
import re
from urllib.parse import urlencode


def prepare(src):
    out = dict(src)
    dc = out.get('datacenter', '')
    audience = out.get('audience_id', '')
    for value, pattern in ((dc, r'us[0-9]+'), (audience, r'[A-Za-z0-9_-]{1,100}'),
                           (out.get('country_merge_tag', ''), r'[A-Za-z0-9_]{1,20}'),
                           (out.get('permission_id', ''), r'[A-Za-z0-9_-]{1,100}')):
        if not isinstance(value, str) or not re.fullmatch(pattern, value):
            raise ValueError('Invalid Mailchimp configuration')
    if not isinstance(out.get('token_env'), str) or not out['token_env']:
        raise ValueError('Missing Mailchimp token environment name')
    out['url'] = f'https://{dc}.api.mailchimp.com/3.0/lists/{audience}/members'
    out['country'] = 'ALL'
    return out


def page(src, cursor, read_json, countries):
    token = os.environ.get(src['token_env'])
    if not token or not token.endswith('-' + src['datacenter']):
        raise PermissionError('Missing or mismatched Mailchimp API key')
    offset = int(cursor or 0)
    if offset < 0:
        raise ValueError('Invalid offset')
    params = {'count': 100, 'offset': offset, 'fields': 'members.id,members.email_address,members.status,members.marketing_permissions,members.merge_fields,members.timestamp_opt,total_items'}
    payload = read_json(src['url'] + '?' + urlencode(params), {'Authorization': 'Bearer ' + token})
    if not isinstance(payload, dict):
        raise ValueError('Malformed Mailchimp response')
    members, total = payload.get('members'), payload.get('total_items')
    if not isinstance(members, list) or type(total) is not int or total < 0 or len(members) > 100:
        raise ValueError('Malformed Mailchimp page')
    if not members and offset < total:
        raise ValueError('Unexpected empty Mailchimp page')
    records, revoked = [], []
    for m in members:
        if not isinstance(m, dict):
            continue
        email, ident = m.get('email_address'), m.get('id')
        if not isinstance(email, str) or not isinstance(ident, str) or not email.strip() or not ident.strip():
            continue
        if m.get('status') in ('unsubscribed', 'cleaned'):
            revoked.append(email)
            continue
        perms = m.get('marketing_permissions')
        if not isinstance(perms, list):
            continue
        matching = [p.get('enabled') for p in perms if isinstance(p, dict) and p.get('marketing_permission_id') == src['permission_id']]
        if False in matching:
            revoked.append(email)
            continue
        if m.get('status') != 'subscribed' or matching != [True]:
            continue
        fields = m.get('merge_fields')
        country = fields.get(src['country_merge_tag']) if isinstance(fields, dict) else None
        country = countries.get(country.strip().casefold()) if isinstance(country, str) else None
        if not country:
            continue
        records.append({'email': email, 'country': country, 'consent': True,
                        'consent_evidence': 'mailchimp:' + src['audience_id'] + ':' + ident + ':' + src['permission_id']})
    nxt = offset + len(members)
    return {'records': records, 'revoked': revoked, 'next_cursor': str(nxt) if nxt < total else None}
