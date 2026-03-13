# Meta Ads Library API Access Token

This file explains how to get a `META_ACCESS_TOKEN` that can call Meta's Ads Library endpoint:

- `https://graph.facebook.com/v25.0/ads_archive`

Important: a normal Facebook or Graph API token is often not enough. Your Meta app and account must be set up specifically for Ads Library API access.

## 1. Read Meta's Ads Library API page

Start here:

- [Meta Ad Library API](https://www.facebook.com/ads/library/api/?source=nav-header)

This is the page Meta references when your token is not authorized for `ads_archive`.

## 2. Make sure your Meta developer account is set up

You need:

1. A Facebook account in good standing.
2. A Meta for Developers account:
   - [Meta for Developers](https://developers.facebook.com/)
3. Identity verification if Meta requires it for your account or use case.

If Meta asks for identity or business verification during setup, finish that first.

## 3. Create a Meta app

In Meta for Developers:

1. Go to `My Apps`.
2. Click `Create App`.
3. Choose the `use case` Meta shows for API and business integrations. Meta changes these labels over time, but you want the path that leads to app setup for developer APIs and business tools.
4. If Meta asks for an app type after that, choose the option best aligned with business/API access. In many cases this is a `Business`-style setup.
5. Fill in:
   - app name
   - contact email
   - business details if requested
6. Create the app.

## 4. Confirm the app was created on the Marketing API path

In the current Meta UI, you may not see an `Add Product` button anymore.

What matters is this:

1. When creating the app, choose the use case `Create & manage ads with Marketing API`.
2. After the app is created, open the app dashboard and confirm you are inside the app created from that Marketing API flow.
3. If Meta shows Marketing API tools, permissions, or related setup automatically, use that app and continue.

So for the newer UI, you usually do not need to manually add `Marketing API` as a separate product. The use case selection is what puts you on the correct path.

Even though you are using Ads Library rather than ad account management, Meta exposes the archive through the Graph API ecosystem, so the Marketing API app path is still the right one.

## 5. Request the right access path for Ads Library

Go back to:

- [Meta Ad Library API](https://www.facebook.com/ads/library/api/?source=nav-header)

Then follow Meta's access steps from there. This part matters because the error:

- `Application does not have permission for this action`

usually means the token exists, but the app has not been granted Ads Library API access yet.

## 6. Generate a user access token

Use one of Meta's token tools:

1. `Graph API Explorer`
   - [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
2. Or the access token tool inside your app / Marketing API tools if Meta shows it there.

When generating the token:

1. Select your app.
2. Sign in with the Facebook account that has access to the app.
3. Generate a user access token.

## 7. Add the needed permissions

When Meta shows available scopes, request the permissions required by the flow it presents.

For Ads Library access, the critical point is not just "having a token", but having the app authorized for Ads Library access. Depending on Meta's current UI and your app state, this may involve:

- Ads Library-specific access flow from the official Ads Library API page
- `ads_read` or related marketing permissions if Meta exposes them in the token tool

If Meta requires app review or additional approval, complete that before expecting `ads_archive` to work.

## 8. Exchange for a longer-lived token if needed

The token you first generate may be short-lived.

If you want a token that lasts longer:

1. Use Meta's token debugging / extension flow.
2. Exchange the short-lived token for a long-lived user token if your app and permissions allow it.

Useful tool:

- [Access Token Debugger](https://developers.facebook.com/tools/debug/accesstoken/)

## 9. Put the token in `.env`

In this project, add it to:

- `MetaAds_library/.env`

Example:

```env
META_ACCESS_TOKEN=your_real_meta_token_here
META_API_VERSION=v25.0
```

## 10. Test the token manually

You can test with a small Ads Library request:

```bash
curl -G \
  -d 'search_terms=california' \
  -d 'ad_type=ALL' \
  -d 'ad_reached_countries=["US"]' \
  -d 'ad_active_status=ALL' \
  -d 'fields=id,page_name,ad_delivery_start_time' \
  -d "access_token=$META_ACCESS_TOKEN" \
  "https://graph.facebook.com/v25.0/ads_archive"
```

## 11. What success looks like

A working token returns JSON containing:

- `data`
- optionally `paging`

Even an empty `data` response is still a valid auth result if there is no matching data.

## 12. What failure looks like

If you get something like:

- `Application does not have permission for this action`
- `OAuthException`
- code `10`

that usually means:

1. the token string is valid enough to reach Meta,
2. but the app or account still does not have Ads Library API authorization.

In other words: this is usually an access approval problem, not a copy-paste problem.

## 13. Recommended troubleshooting order

1. Confirm the token belongs to the correct app in the Access Token Debugger.
2. Confirm the app has the Marketing API product added.
3. Revisit the official Ads Library API page and complete any access steps there.
4. Check whether Meta is asking for app review, identity verification, or business verification.
5. Generate a fresh token after access is approved.
6. Re-test the `ads_archive` endpoint.

## 14. After the token works

Once `ads_archive` returns real data, this project can use it via:

```bash
meta-ads fetch --query "anti aging serum" --country US --media-type VIDEO --limit-pages 1
```

## Notes

- Tokens expire, so a previously working token may stop working later.
- Keep `META_ACCESS_TOKEN` only in `.env`, never commit it.
- Ads Library access rules can change over time, so the official Meta Ads Library API page should always be treated as the source of truth.
