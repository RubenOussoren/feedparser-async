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
    const compactMode = this.config.compact === true;
    const showRefresh = this.config.show_refresh !== false;
    const feedTitle = stateObj.attributes.feed_title || stateObj.attributes.friendly_name || 'Feed';
    const feedLink = stateObj.attributes.feed_link || '#';
    const lastEntryDate = stateObj.attributes.last_entry_date || '';

    let entriesHtml = '';
    if (entries.length === 0) {
      entriesHtml = `
        <div class="no-entries">
          <ha-icon icon="mdi:rss-off"></ha-icon>
          <span>No entries available</span>
        </div>
      `;
    } else {
      entries.slice(0, maxEntries).forEach((entry, index) => {
        const title = entry.title || 'Untitled';
        const link = entry.link || '#';
        const summary = entry.summary || entry.description || '';
        const image = entry.image || '';
        const published = entry.published || entry.updated || '';
        const author = entry.author || '';

        if (compactMode) {
          entriesHtml += `
            <div class="feed-entry compact ${index === 0 ? 'first-entry' : ''}">
              <div class="entry-content">
                <a href="${link}" target="_blank" rel="noopener noreferrer" class="entry-title">
                  ${title}
                </a>
                ${showDate && published ? `<span class="entry-date-inline">${published}</span>` : ''}
              </div>
            </div>
          `;
        } else {
          entriesHtml += `
            <div class="feed-entry ${index === 0 ? 'first-entry' : ''}">
              ${showImages && image ? `
                <div class="entry-image">
                  <img src="${image}" alt="" loading="lazy" onerror="this.parentElement.style.display='none'">
                </div>
              ` : ''}
              <div class="entry-content">
                <div class="entry-header">
                  <a href="${link}" target="_blank" rel="noopener noreferrer" class="entry-title">
                    ${title}
                  </a>
                  <div class="entry-meta">
                    ${showDate && published ? `<span class="entry-date">${published}</span>` : ''}
                    ${author ? `<span class="entry-author">by ${author}</span>` : ''}
                  </div>
                </div>
                ${showSummary && summary ? `
                  <div class="entry-summary">${this.stripHtml(summary)}</div>
                ` : ''}
              </div>
            </div>
          `;
        }
      });
    }

    const headerHtml = `
      <div class="card-header">
        <div class="header-left">
          <ha-icon icon="mdi:rss" class="feed-icon"></ha-icon>
          <div class="header-text">
            <a href="${feedLink}" target="_blank" rel="noopener noreferrer" class="card-title">
              ${this.config.title || feedTitle}
            </a>
            ${lastEntryDate ? `<div class="last-updated">Latest: ${lastEntryDate}</div>` : ''}
          </div>
        </div>
        <div class="header-right">
          <div class="card-count">${stateObj.state}</div>
          ${showRefresh ? `
            <ha-icon-button class="refresh-btn" @click="${() => this.refreshFeed()}">
              <ha-icon icon="mdi:refresh"></ha-icon>
            </ha-icon-button>
          ` : ''}
        </div>
      </div>
    `;

    this.innerHTML = `
      <ha-card>
        ${headerHtml}
        <div class="card-content ${compactMode ? 'compact-content' : ''}">
          ${entriesHtml}
        </div>
      </ha-card>
    `;

    // Add refresh button click handler
    if (showRefresh) {
      const refreshBtn = this.querySelector('.refresh-btn');
      if (refreshBtn) {
        refreshBtn.addEventListener('click', () => this.refreshFeed());
      }
    }

    this.addStyles();
  }

  refreshFeed() {
    if (this._hass && this.config.entity) {
      this._hass.callService('homeassistant', 'update_entity', {
        entity_id: this.config.entity
      });
    }
  }

  addStyles() {
    if (this.querySelector('style')) return;

    const style = document.createElement('style');
    style.textContent = `
      feedparser-card {
        display: block;
      }
      feedparser-card ha-card {
        padding: 0;
        overflow: hidden;
      }
      feedparser-card .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 16px;
        background: var(--card-background-color, var(--ha-card-background));
        border-bottom: 1px solid var(--divider-color);
      }
      feedparser-card .header-left {
        display: flex;
        align-items: center;
        gap: 12px;
        min-width: 0;
        flex: 1;
      }
      feedparser-card .feed-icon {
        color: var(--primary-color);
        --mdc-icon-size: 24px;
        flex-shrink: 0;
      }
      feedparser-card .header-text {
        min-width: 0;
        flex: 1;
      }
      feedparser-card .card-title {
        font-weight: 500;
        font-size: 16px;
        color: var(--primary-text-color);
        text-decoration: none;
        display: block;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      feedparser-card .card-title:hover {
        color: var(--primary-color);
      }
      feedparser-card .last-updated {
        font-size: 12px;
        color: var(--secondary-text-color);
        margin-top: 2px;
      }
      feedparser-card .header-right {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-shrink: 0;
      }
      feedparser-card .card-count {
        background: var(--primary-color);
        color: var(--text-primary-color, white);
        font-size: 14px;
        font-weight: 500;
        padding: 4px 10px;
        border-radius: 12px;
        min-width: 24px;
        text-align: center;
      }
      feedparser-card .refresh-btn {
        --mdc-icon-button-size: 36px;
        --mdc-icon-size: 20px;
        color: var(--secondary-text-color);
      }
      feedparser-card .refresh-btn:hover {
        color: var(--primary-color);
      }
      feedparser-card .card-content {
        padding: 0;
        max-height: 400px;
        overflow-y: auto;
      }
      feedparser-card .card-content.compact-content {
        max-height: 300px;
      }
      feedparser-card .feed-entry {
        display: flex;
        padding: 12px 16px;
        border-bottom: 1px solid var(--divider-color);
        transition: background-color 0.15s ease;
        gap: 12px;
      }
      feedparser-card .feed-entry:last-child {
        border-bottom: none;
      }
      feedparser-card .feed-entry:hover {
        background-color: var(--secondary-background-color, rgba(0,0,0,0.04));
      }
      feedparser-card .feed-entry.first-entry {
        border-left: 3px solid var(--primary-color);
        padding-left: 13px;
      }
      feedparser-card .feed-entry.compact {
        padding: 8px 16px;
        align-items: center;
      }
      feedparser-card .feed-entry.compact .entry-content {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
      }
      feedparser-card .feed-entry.compact .entry-title {
        font-size: 14px;
        margin: 0;
      }
      feedparser-card .entry-date-inline {
        font-size: 11px;
        color: var(--secondary-text-color);
        white-space: nowrap;
      }
      feedparser-card .entry-image {
        flex-shrink: 0;
        width: 80px;
        height: 60px;
        overflow: hidden;
        border-radius: 6px;
        background: var(--secondary-background-color);
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
        margin-bottom: 6px;
      }
      feedparser-card .entry-title {
        display: block;
        font-weight: 500;
        font-size: 14px;
        line-height: 1.4;
        color: var(--primary-text-color);
        text-decoration: none;
        margin-bottom: 4px;
      }
      feedparser-card .entry-title:hover {
        color: var(--primary-color);
      }
      feedparser-card .entry-meta {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
      }
      feedparser-card .entry-date {
        font-size: 11px;
        color: var(--secondary-text-color);
      }
      feedparser-card .entry-author {
        font-size: 11px;
        color: var(--secondary-text-color);
      }
      feedparser-card .entry-summary {
        font-size: 13px;
        color: var(--secondary-text-color);
        line-height: 1.5;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
      }
      feedparser-card .no-entries {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 32px;
        color: var(--secondary-text-color);
        gap: 8px;
      }
      feedparser-card .no-entries ha-icon {
        --mdc-icon-size: 48px;
        opacity: 0.5;
      }
      feedparser-card .error {
        padding: 16px;
        color: var(--error-color);
        text-align: center;
      }

      /* Scrollbar styling */
      feedparser-card .card-content::-webkit-scrollbar {
        width: 6px;
      }
      feedparser-card .card-content::-webkit-scrollbar-track {
        background: transparent;
      }
      feedparser-card .card-content::-webkit-scrollbar-thumb {
        background: var(--scrollbar-thumb-color, rgba(0,0,0,0.2));
        border-radius: 3px;
      }
      feedparser-card .card-content::-webkit-scrollbar-thumb:hover {
        background: var(--primary-color);
      }

      /* Mobile responsiveness */
      @media (max-width: 500px) {
        feedparser-card .entry-image {
          width: 60px;
          height: 45px;
        }
        feedparser-card .card-header {
          padding: 12px;
        }
        feedparser-card .feed-entry {
          padding: 10px 12px;
        }
        feedparser-card .entry-title {
          font-size: 13px;
        }
        feedparser-card .entry-summary {
          font-size: 12px;
          -webkit-line-clamp: 2;
        }
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

  static getConfigElement() {
    return document.createElement('feedparser-card-editor');
  }

  static getStubConfig() {
    return {
      entity: '',
      title: '',
      max_entries: 5,
      show_images: true,
      show_summary: true,
      show_date: true,
      compact: false,
      show_refresh: true
    };
  }
}

customElements.define('feedparser-card', FeedParserCard);

// Card configuration UI
class FeedParserCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = { ...config };
    this.render();
  }

  set hass(hass) {
    this._hass = hass;
    if (this._entityPicker) {
      this._entityPicker.hass = hass;
    }
  }

  render() {
    if (!this._config) return;

    this.innerHTML = `
      <div class="card-config">
        <div class="entity-row">
          <label>Entity *</label>
          <div id="entity-picker-container"></div>
        </div>

        <ha-textfield
          id="title-input"
          label="Title (optional)"
        ></ha-textfield>

        <ha-textfield
          id="max-entries-input"
          label="Max entries"
          type="number"
        ></ha-textfield>

        <ha-formfield label="Show images">
          <ha-switch id="show-images-switch"></ha-switch>
        </ha-formfield>

        <ha-formfield label="Show summary">
          <ha-switch id="show-summary-switch"></ha-switch>
        </ha-formfield>

        <ha-formfield label="Show date">
          <ha-switch id="show-date-switch"></ha-switch>
        </ha-formfield>

        <ha-formfield label="Compact mode">
          <ha-switch id="compact-switch"></ha-switch>
        </ha-formfield>

        <ha-formfield label="Show refresh button">
          <ha-switch id="show-refresh-switch"></ha-switch>
        </ha-formfield>
      </div>
      <style>
        .card-config {
          display: flex;
          flex-direction: column;
          gap: 16px;
          padding: 16px;
        }
        .entity-row {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        .entity-row label {
          font-weight: 500;
          font-size: 12px;
          color: var(--secondary-text-color);
        }
        ha-formfield {
          display: flex;
          align-items: center;
        }
        ha-entity-picker {
          display: block;
          width: 100%;
        }
      </style>
    `;

    // Create and configure entity picker
    const container = this.querySelector('#entity-picker-container');
    this._entityPicker = document.createElement('ha-entity-picker');
    this._entityPicker.hass = this._hass;
    this._entityPicker.value = this._config.entity || '';
    this._entityPicker.allowCustomEntity = true;
    this._entityPicker.includeDomains = ['sensor'];
    this._entityPicker.addEventListener('value-changed', (e) => {
      this._updateConfig('entity', e.detail.value);
    });
    container.appendChild(this._entityPicker);

    // Title input
    const titleInput = this.querySelector('#title-input');
    titleInput.value = this._config.title || '';
    titleInput.addEventListener('input', (e) => {
      this._updateConfig('title', e.target.value);
    });

    // Max entries input
    const maxEntriesInput = this.querySelector('#max-entries-input');
    maxEntriesInput.value = this._config.max_entries || '';
    maxEntriesInput.addEventListener('input', (e) => {
      const val = e.target.value ? parseInt(e.target.value, 10) : undefined;
      this._updateConfig('max_entries', val);
    });

    // Switch inputs
    const showImagesSwitch = this.querySelector('#show-images-switch');
    showImagesSwitch.checked = this._config.show_images !== false;
    showImagesSwitch.addEventListener('change', (e) => {
      this._updateConfig('show_images', e.target.checked);
    });

    const showSummarySwitch = this.querySelector('#show-summary-switch');
    showSummarySwitch.checked = this._config.show_summary !== false;
    showSummarySwitch.addEventListener('change', (e) => {
      this._updateConfig('show_summary', e.target.checked);
    });

    const showDateSwitch = this.querySelector('#show-date-switch');
    showDateSwitch.checked = this._config.show_date !== false;
    showDateSwitch.addEventListener('change', (e) => {
      this._updateConfig('show_date', e.target.checked);
    });

    const compactSwitch = this.querySelector('#compact-switch');
    compactSwitch.checked = this._config.compact === true;
    compactSwitch.addEventListener('change', (e) => {
      this._updateConfig('compact', e.target.checked);
    });

    const showRefreshSwitch = this.querySelector('#show-refresh-switch');
    showRefreshSwitch.checked = this._config.show_refresh !== false;
    showRefreshSwitch.addEventListener('change', (e) => {
      this._updateConfig('show_refresh', e.target.checked);
    });
  }

  _updateConfig(key, value) {
    if (!this._config) return;

    const newConfig = { ...this._config };
    if (value === '' || value === undefined || value === null) {
      delete newConfig[key];
    } else {
      newConfig[key] = value;
    }

    this._config = newConfig;
    const event = new CustomEvent('config-changed', {
      detail: { config: newConfig },
      bubbles: true,
      composed: true
    });
    this.dispatchEvent(event);
  }
}

customElements.define('feedparser-card-editor', FeedParserCardEditor);

// Register card with Home Assistant
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'feedparser-card',
  name: 'Feedparser Card',
  description: 'Display RSS/Atom feed entries in a beautiful card',
  preview: true,
  documentationURL: 'https://github.com/custom-components/feedparser'
});
