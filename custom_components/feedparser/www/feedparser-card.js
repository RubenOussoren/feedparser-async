/* eslint-disable @typescript-eslint/no-this-alias */
/* eslint-disable @typescript-eslint/explicit-module-boundary-types */
/* eslint-disable @typescript-eslint/no-explicit-any */
class FeedParserCard extends HTMLElement {
  setConfig(config) {
    this.config = config;
    if (!this.config.entity) {
      throw new Error('Entity is required');
    }
  }

  set hass(hass) {
    this._hass = hass;
    this.updateCard();
  }

  get hass() {
    return this._hass;
  }

  updateCard() {
    if (!this._hass || !this.config) {
      return;
    }

    const entityId = this.config.entity;
    const stateObj = this._hass.states[entityId];

    if (!stateObj) {
      this.innerHTML = `
        <ha-card>
          <div class="card-content">
            <div class="error">Entity ${entityId} not found</div>
          </div>
        </ha-card>
      `;
      return;
    }

    const entries = stateObj.attributes.entries || [];
    const maxEntries = this.config.max_entries || entries.length;
    const showImages = this.config.show_images !== false;
    const showSummary = this.config.show_summary !== false;
    const showDate = this.config.show_date !== false;

    let entriesHtml = '';
    if (entries.length === 0) {
      entriesHtml = '<div class="no-entries">No entries available</div>';
    } else {
      entries.slice(0, maxEntries).forEach((entry, index) => {
        const title = entry.title || 'Untitled';
        const link = entry.link || '#';
        const summary = entry.summary || entry.description || '';
        const image = entry.image || '';
        const published = entry.published || entry.updated || '';
        const author = entry.author || '';

        entriesHtml += `
          <div class="feed-entry ${index === 0 ? 'first-entry' : ''}">
            ${showImages && image ? `
              <div class="entry-image">
                <img src="${image}" alt="${title}" onerror="this.style.display='none'">
              </div>
            ` : ''}
            <div class="entry-content">
              <div class="entry-header">
                <a href="${link}" target="_blank" rel="noopener noreferrer" class="entry-title">
                  ${title}
                </a>
                ${showDate && published ? `
                  <div class="entry-date">${published}</div>
                ` : ''}
                ${author ? `
                  <div class="entry-author">${author}</div>
                ` : ''}
              </div>
              ${showSummary && summary ? `
                <div class="entry-summary">${this.stripHtml(summary)}</div>
              ` : ''}
            </div>
          </div>
        `;
      });
    }

    this.innerHTML = `
      <ha-card>
        <div class="card-header">
          <div class="card-title">${this.config.title || stateObj.attributes.friendly_name || 'Feed'}</div>
          <div class="card-count">${stateObj.state} entries</div>
        </div>
        <div class="card-content">
          ${entriesHtml}
        </div>
      </ha-card>
    `;

    const style = document.createElement('style');
    style.textContent = `
      feedparser-card {
        display: block;
      }
      feedparser-card ha-card {
        padding: 0;
      }
      feedparser-card .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 16px;
        border-bottom: 1px solid var(--divider-color);
      }
      feedparser-card .card-title {
        font-weight: 500;
        font-size: 16px;
      }
      feedparser-card .card-count {
        color: var(--secondary-text-color);
        font-size: 14px;
      }
      feedparser-card .card-content {
        padding: 0;
      }
      feedparser-card .feed-entry {
        display: flex;
        padding: 16px;
        border-bottom: 1px solid var(--divider-color);
        transition: background-color 0.2s;
      }
      feedparser-card .feed-entry:hover {
        background-color: var(--card-background-color, var(--primary-background-color));
      }
      feedparser-card .feed-entry.first-entry {
        border-top: 2px solid var(--primary-color);
      }
      feedparser-card .entry-image {
        flex-shrink: 0;
        width: 120px;
        height: 80px;
        margin-right: 16px;
        overflow: hidden;
        border-radius: 4px;
      }
      feedparser-card .entry-image img {
        width: 100%;
        height: 100%;
        object-fit: cover;
      }
      feedparser-card .entry-content {
        flex: 1;
        min-width: 0;
      }
      feedparser-card .entry-header {
        margin-bottom: 8px;
      }
      feedparser-card .entry-title {
        display: block;
        font-weight: 500;
        font-size: 16px;
        color: var(--primary-text-color);
        text-decoration: none;
        margin-bottom: 4px;
        word-wrap: break-word;
      }
      feedparser-card .entry-title:hover {
        color: var(--primary-color);
      }
      feedparser-card .entry-date {
        font-size: 12px;
        color: var(--secondary-text-color);
        margin-top: 4px;
      }
      feedparser-card .entry-author {
        font-size: 12px;
        color: var(--secondary-text-color);
        margin-top: 2px;
      }
      feedparser-card .entry-summary {
        font-size: 14px;
        color: var(--secondary-text-color);
        line-height: 1.5;
        margin-top: 8px;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
      }
      feedparser-card .no-entries {
        padding: 32px;
        text-align: center;
        color: var(--secondary-text-color);
      }
      feedparser-card .error {
        padding: 16px;
        color: var(--error-color);
      }
    `;
    this.appendChild(style);
  }

  stripHtml(html) {
    const tmp = document.createElement('DIV');
    tmp.innerHTML = html;
    return tmp.textContent || tmp.innerText || '';
  }

  getCardSize() {
    return 3;
  }
}

customElements.define('feedparser-card', FeedParserCard);

