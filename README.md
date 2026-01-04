# sensor.feedparser (Async Fork)

> Modernized fork of [custom-components/feedparser](https://github.com/custom-components/feedparser) with async/await support for Home Assistant 2026+

RSS feed custom component for [Home Assistant](https://www.home-assistant.io/) which can be used in conjunction with the custom Lovelace card included or [list-card](https://github.com/custom-cards/list-card)

[![GitHub Release][releases-shield]][releases]
[![License][license-shield]](LICENSE.md)

![Project Maintenance][maintenance-shield]
[![GitHub Activity][commits-shield]][commits]

## Features

- **Config Flow UI** - Add and manage feeds through Settings > Integrations
- **Async/await pattern** - Non-blocking I/O using aiohttp instead of requests
- **DataUpdateCoordinator** - Centralized feed fetching with proper async handling
- **Device Registry** - Feeds appear as devices with proper grouping
- **Unique IDs** - Entities are editable in the UI and survive restarts
- **Retry logic** - Exponential backoff (3 retries) for transient network failures
- **Better error handling** - Graceful handling of timeouts, malformed feeds, and network errors
- **Proper shutdown** - No more hanging threads during Home Assistant restart
- **Session reuse** - Efficient connection pooling with aiohttp ClientSession
- **Feed validation** - Checks for malformed feeds using feedparser's bozo flag
- **Custom Lovelace Card** - Beautiful feed display card included

## Installation

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

1. Open HACS Settings and add this repository (https://github.com/RubenOussoren/feedparser-async)
   as a Custom Repository (use **Integration** as the category).
2. The `feedparser` page should automatically load (or find it in the HACS Store)
3. Click `Install`
4. Restart Home Assistant

### Manual Installation

```bash
cd /path/to/homeassistant/config/custom_components
git clone -b async-modernization https://github.com/RubenOussoren/feedparser-async.git feedparser_temp
mv feedparser_temp/custom_components/feedparser ./feedparser
rm -rf feedparser_temp
```

Then restart Home Assistant.

## Configuration

Add and manage feeds entirely through the Home Assistant UI:

1. Go to **Settings** > **Devices & Services**
2. Click **Add Integration**
3. Search for **Feedparser**
4. Enter your feed details:
   - **Feed Name**: A friendly name for this feed
   - **Feed URL**: The RSS/Atom feed URL
5. Click **Submit**

You can edit feed settings later by clicking on the integration and selecting **Options**:

| Option          | Default              | Description                     |
| --------------- | -------------------- | ------------------------------- |
| Date Format     | `%a, %b %d %I:%M %p` | strftime format for dates       |
| Local Time      | `false`              | Convert dates to local timezone |
| Max Entries     | `50`                 | Limit number of entries         |
| Update Interval | `1 hour`             | How often to fetch the feed     |

## Sensor Attributes

Each feed sensor provides:

- **State**: Number of entries
- **Unit**: `entries`
- **Device**: Feeds are grouped under a "Feedparser" device in the device registry
- **Unique ID**: Based on feed URL hash (entities survive restarts and are editable)
- **Attributes**:
  - `entries`: List of feed items (title, link, summary, published, image, author)
  - `feed_url`: The RSS feed URL
  - `feed_title`: The feed's title
  - `feed_link`: The feed's website link
  - `feed_description`: The feed's description
  - `last_entry_date`: Date of the most recent entry

## Using with Lovelace

### Custom Feedparser Card (Recommended)

The integration includes a custom Lovelace card for displaying feeds beautifully.

**Installation (HACS users):**

1. Go to **Settings** → **Dashboards** → **Resources** (click the 3-dot menu)
2. Click **Add Resource**
3. Enter the URL: `/local/community/feedparser/www/feedparser-card.js`
4. Select **JavaScript Module**
5. Click **Create**
6. **Refresh your browser** (Ctrl+Shift+R or Cmd+Shift+R)

**Installation (Manual install users):**

After restarting Home Assistant, the card auto-registers at `/feedparser/feedparser-card.js`. If it doesn't work, manually add the resource:

1. Copy `custom_components/feedparser/www/feedparser-card.js` to your `www` folder
2. Add resource: `/local/feedparser-card.js` as JavaScript Module

**Add the card to your dashboard:**

```yaml
type: custom:feedparser-card
entity: sensor.tech_headlines
title: Tech News
max_entries: 10
show_images: true
show_summary: true
show_date: true
compact: false
show_refresh: true
```

**Card Options:**

| Option         | Type    | Default      | Description                |
| -------------- | ------- | ------------ | -------------------------- |
| `entity`       | string  | **Required** | Feed sensor entity ID      |
| `title`        | string  | Entity name  | Card title                 |
| `max_entries`  | number  | All entries  | Maximum entries to display |
| `show_images`  | boolean | `true`       | Show entry images          |
| `show_summary` | boolean | `true`       | Show entry summaries       |
| `show_date`    | boolean | `true`       | Show publication dates     |
| `compact`      | boolean | `false`      | Compact list view          |
| `show_refresh` | boolean | `true`       | Show manual refresh button |

### With list-card

```yaml
type: custom:list-card
entity: sensor.tech_headlines
title: Tech News
feed_attribute: entries
columns:
  - field: image
    style:
      - width: 80px
  - field: title
  - field: published
```

### In Templates

```yaml
# Get first headline title
{{ state_attr('sensor.tech_headlines', 'entries')[0].title }}

# Get first headline link
{{ state_attr('sensor.tech_headlines', 'entries')[0].link }}

# Loop through headlines
{% for entry in state_attr('sensor.tech_headlines', 'entries')[:5] %}
- {{ entry.title }}
{% endfor %}
```

## Troubleshooting

### ModuleNotFoundError on first boot

This is normal for custom components. Restart Home Assistant to resolve.

### Feed not updating

- Check the feed URL is accessible
- Review Home Assistant logs for errors
- The integration will retry 3 times with exponential backoff

### Dates showing incorrectly

- Edit the integration options and try different date format strings
- Enable "Local Time" for local timezone conversion

### Empty entries

- Verify the feed has content by visiting the URL in a browser
- Some feeds may not include all fields (summary, image, etc.)

## Credits

- Original integration by [@iantrich](https://github.com/iantrich) and [@ogajduse](https://github.com/ogajduse)
- Async modernization by [@RubenOussoren](https://github.com/RubenOussoren)

[commits-shield]: https://img.shields.io/github/commit-activity/y/RubenOussoren/feedparser-async.svg?style=for-the-badge
[commits]: https://github.com/RubenOussoren/feedparser-async/commits/async-modernization
[discord]: https://discord.gg/Qa5fW2R
[discord-shield]: https://img.shields.io/discord/330944238910963714.svg?style=for-the-badge
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/t/custom-component-rss-feed-parser/64637
[license-shield]: https://img.shields.io/github/license/RubenOussoren/feedparser-async.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Ruben%20Oussoren%20%40RubenOussoren-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/RubenOussoren/feedparser-async.svg?style=for-the-badge
[releases]: https://github.com/RubenOussoren/feedparser-async/releases
