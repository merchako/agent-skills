# Scriptura email signature

A compact two-column signature: square photo left; name, title, org, and contact links right, all small and grey under the bold name. Fill every `{{…}}`; drop any line or link the person doesn't want (Calendly, location, phone) along with its `&nbsp;` separator.

| Placeholder        | Value                                                                         |
| ------------------ | ----------------------------------------------------------------------------- |
| `{{NAME}}`         | Full name                                                                     |
| `{{TITLE}}`        | Job title at Scriptura                                                        |
| `{{PHOTO_URL}}`    | Public image URL (see _Photo_ below)                                          |
| `{{PHONE_E164}}`   | Dial string, digits only with `+` country code: `+18175551234`                |
| `{{PHONE_PRETTY}}` | Display form: `+1 817 555-1234`                                               |
| `{{CITY}}`         | `City, Country`, as displayed                                                 |
| `{{CITY_URL}}`     | `https://maps.google.com/?q=` + URL-encoded `{{CITY}}`                        |
| `{{UTC}}`          | Offset label, e.g. `UTC-6`; note DST if the zone has it (`UTC-5/-4`)           |
| `{{TIME_URL}}`     | `https://time.is/<City_or_Country>`                                           |
| `{{BOOKING_URL}}`  | Calendly / booking page                                                       |

Verify `{{PHONE_E164}}` dials the same number `{{PHONE_PRETTY}}` shows: a mismatched `tel:` link is the classic copy-paste bug in this template.

```html
<table cellspacing="0" cellpadding="0" style="font-family: inherit;"><tbody><tr>
<td style="vertical-align: top;"><img alt="{{NAME}}" src="{{PHOTO_URL}}" width="56" height="56" style="max-width: 80px; max-height: 80px; margin-right: 20px; border-radius: 8px;"></td>
<td>
<div><b>{{NAME}}&nbsp;</b><span style="font-size: 0.8em; margin-left: 8px; color: grey;">{{TITLE}}</span></div>
<div style="font-size: 0.8em; color: grey; min-width: 200px; max-width: 400px;">
<div style="margin-top: 4px;"><span style="margin-right: 8px;">Scriptura</span>&nbsp;<a href="https://www.scriptura.org/" target="_blank" style="color: grey; margin-right: 8px;">scriptura.org</a></div>
<div style="margin-top: 4px;"><a href="tel:{{PHONE_E164}}" target="_blank" style="color: grey; margin-right: 8px;">{{PHONE_PRETTY}}</a>&nbsp;<a href="{{CITY_URL}}" target="_blank" style="color: grey; margin-right: 8px;">{{CITY}}</a>&nbsp;<a href="{{TIME_URL}}" target="_blank" style="color: grey; margin-right: 8px;">{{UTC}}</a>&nbsp;<a href="{{BOOKING_URL}}" target="_blank" style="color: grey; margin-right: 8px;">Calendly</a></div>
</div>
</td>
</tr></tbody></table>
```

## Photo

`{{PHOTO_URL}}` must be publicly fetchable. Options, best first:

1. The Scriptura Google account avatar (the badged profile photo, once set): the _My picture_ image on Gmail → Settings → General, or right-click the account-menu avatar → _Copy image address_. It looks like `https://lh3.googleusercontent.com/a/<id>=s96`; replace the trailing size with `=s112-c` (2× the 56px display). Use the `/a/<id>` URL, not an `/ogw/` one. It updates whenever the profile photo does.
2. Any public host the person controls.

Gmail's signature editor can also insert an uploaded image directly (_Insert image_ → _Upload_); in that case leave the `<img>` out of the HTML and insert the photo in the editor after pasting.

## Install (Gmail)

Check _Settings → General → Signature_ first: if a signature already exists, show it to the person before replacing it.

### By hand

1. Write the filled HTML to a `.html` file and open it in a browser.
2. Select the rendered signature (not the source), copy.
3. Gmail (scriptura.org account) → Settings → See all settings → General → Signature → _Create new_ → paste.
4. Set it as the default for new emails and replies → _Save changes_ at the bottom of the page.

### With browser automation

Same flow, minus the clipboard:

1. Open `https://mail.google.com/mail/u/<N>/#settings/general`, where `<N>` is the scriptura.org account's index (an email address in place of `<N>` errors). Confirm the page title names the scriptura.org address.
2. _Create new_ → name it `Scriptura` → _Create_.
3. Fill the editor (`div[contenteditable][aria-label="Signature"]`) by dispatching a synthetic paste: a `ClipboardEvent('paste')` whose `DataTransfer` carries the HTML as `text/html`. Setting `innerHTML` or `execCommand('insertHTML')` fails — Gmail enforces Trusted Types.
4. Set both _Signature defaults_ `<select>`s to `Scriptura` (set `value`, dispatch `change`), click _Save Changes_.

Done when a reload of the settings page shows the signature with every link intact and both defaults set to `Scriptura`.
