# sensor.feedparser (Async Fork)

> Modernized fork of [custom-components/feedparser](https://github.com/custom-components/feedparser) with async/await support for Home Assistant 2026+

RSS feed custom component for [Home Assistant](https://www.home-assistant.io/) which can be used in conjunction with the custom [Lovelace](https://www.home-assistant.io/lovelace) [list-card](https://github.com/custom-cards/list-card)

[![GitHub Release][releases-shield]][releases]
[![License][license-shield]](LICENSE.md)

![Project Maintenance][maintenance-shield]
[![GitHub Activity][commits-shield]][commits]

## Changes from Original

- **Config Flow UI** - Add and manage feeds through Settings > Integrations (no YAML required)
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

### Manual Installation

```bash
cd /path/to/homeassistant/config/custom_components
git clone -b async-modernization https://github.com/RubenOussoren/feedparser-async.git feedparser_temp
mv feedparser_temp/custom_components/feedparser ./feedparser
rm -rf feedparser_temp
```

Then restart Home Assistant.

## Configuration

### Config Flow (Recommended - No YAML Required!)

**You no longer need YAML configuration!** Add and manage feeds entirely through the Home Assistant UI.

1. Go to **Settings** > **Devices & Services**
2. Click **Add Integration**
3. Search for **Feedparser**
4. Enter your feed details:
   - **Feed Name**: A friendly name for this feed
   - **Feed URL**: The RSS/Atom feed URL
   - **Date Format**: Optional strftime format (default: `%a, %b %d %I:%M %p`)
   - **Other options**: Configure as needed
5. Click **Submit**

You can edit feed settings later by clicking on the integration and selecting **Options**.

### YAML Configuration (Optional - For Advanced Users)

YAML configuration is still supported for backward compatibility or if you prefer YAML. Existing YAML configs will continue to work and can be imported into Config Flow automatically.

**Example configuration.yaml:**

```yaml
sensor:
  - platform: feedparser
    name: Engineering Feed
    feed_url: "https://www.sciencedaily.com/rss/matter_energy/engineering.xml"
    date_format: "%a, %d %b %Y %H:%M:%S"
    local_time: true
    scan_interval:
      hours: 6
    inclusions:
      - title
      - link
      - summary
      - published

  - platform: feedparser
    name: World News
    feed_url: "https://feeds.npr.org/1004/rss.xml"
    local_time: true
    show_topn: 10
    inclusions:
      - title
      - link
      - summary
      - published
      - author
      - content
      - image
```

## Field Mapping

Feedparser normalizes RSS field names. Use these names in your `inclusions`:

| RSS Field         | Use in Config | Description                            |
| ----------------- | ------------- | -------------------------------------- |
| `title`           | `title`       | Article headline                       |
| `link`            | `link`        | URL to article                         |
| `description`     | `summary`     | Short description/excerpt              |
| `content:encoded` | `content`     | Full article content (HTML, as a list) |
| `pubDate`         | `published`   | Publication date                       |
| `dc:creator`      | `author`      | Writer's name                          |
| `guid`            | `id`          | Unique identifier                      |
| `enclosure`       | `image`       | Article thumbnail/image                |
| `updated`         | `updated`     | Last updated date                      |
| `created`         | `created`     | Creation date                          |
| `expired`         | `expired`     | Expiration date                        |

> **Note:** The `content` field is returned as a list of dictionaries. Access the HTML with `entry.content[0].value` in templates.

### Image Handling

Add `image` to your `inclusions` list to extract images from feed entries. The integration will:

1. Look for enclosures with image MIME types
2. Search for `<img>` tags in the summary
3. Fall back to the Home Assistant logo if no image is found

## Configuration Variables

| Key             | Required | Default              | Description                     |
| --------------- | -------- | -------------------- | ------------------------------- |
| `platform`      | Yes      | -                    | Must be `feedparser`            |
| `name`          | Yes      | -                    | Name for your feed sensor       |
| `feed_url`      | Yes      | -                    | The RSS/Atom feed URL           |
| `date_format`   | No       | `%a, %b %d %I:%M %p` | strftime format for dates       |
| `local_time`    | No       | `false`              | Convert dates to local timezone |
| `show_topn`     | No       | all                  | Limit number of entries         |
| `inclusions`    | No       | all fields           | Fields to include               |
| `exclusions`    | No       | none                 | Fields to exclude               |
| `scan_interval` | No       | 1 hour               | Update frequency                |

## Sensor Attributes

Each feed sensor provides:

- **State**: Number of entries
- **Unit**: `entries`
- **Device**: Feeds are grouped under a "Feedparser" device in the device registry
- **Unique ID**: Based on feed URL hash (entities survive restarts and are editable)
- **Attributes**:
  - `entries`: List of feed items with requested fields
  - `attribution`: Data source attribution

## Example: Morning Briefing

```yaml
sensor:
  # Finance News
  - platform: feedparser
    name: Finance Headlines
    feed_url: "https://www.bnnbloomberg.ca/arc/outboundfeeds/rss/?outputType=xml"
    date_format: "%a, %d %b %Y %H:%M:%S"
    local_time: true
    scan_interval:
      hours: 3
    inclusions:
      - title
      - link
      - summary
      - published
      - author
      - image

  # World News
  - platform: feedparser
    name: World Headlines
    feed_url: "https://feeds.npr.org/1004/rss.xml"
    date_format: "%a, %d %b %Y %H:%M:%S"
    local_time: true
    scan_interval:
      hours: 3
    inclusions:
      - title
      - link
      - summary
      - published
      - author
      - content
      - image

  # Tech News
  - platform: feedparser
    name: Tech Headlines
    feed_url: "https://feeds.arstechnica.com/arstechnica/technology-lab"
    date_format: "%a, %d %b %Y %H:%M:%S"
    local_time: true
    scan_interval:
      hours: 6
    inclusions:
      - title
      - link
      - summary
      - published
      - author
      - image
```

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

- Try different `date_format` strings
- Enable `local_time: true` for local timezone conversion
- Omit timezone specifiers (`%Z`, `%z`) - feedparser handles them internally

### Empty entries

- Verify the feed has content by visiting the URL in a browser
- Check that `inclusions` use the correct feedparser field names (e.g., `summary` not `description`)

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
