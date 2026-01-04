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

// Card configuration UI - uses native HTML elements for reliability
class FeedParserCardEditor extends HTMLElement {
  constructor() {
    super();
    this._config = {};
    this._hass = null;
    this._rendered = false;
  }

  setConfig(config) {
    this._config = { ...config };
    if (this._hass) {
      this._render();
    }
  }

  set hass(hass) {
    this._hass = hass;
    if (this._config && !this._rendered) {
      this._render();
    }
  }

  _getFeedparserEntities() {
    if (!this._hass) return [];
    return Object.keys(this._hass.states)
      .filter(entityId => {
        const state = this._hass.states[entityId];
        return entityId.startsWith('sensor.') && 
          state.attributes && 
          state.attributes.entries !== undefined;
      })
      .sort();
  }

  _render() {
    this._rendered = true;
    const entities = this._getFeedparserEntities();
    
    const entityOptions = entities.map(e => {
      const friendly = this._hass.states[e]?.attributes?.friendly_name || e;
      const selected = e === this._config.entity ? 'selected' : '';
      return `<option value="${e}" ${selected}>${friendly}</option>`;
    }).join('');

    this.innerHTML = `
      <style>
        .editor-container {
          display: flex;
          flex-direction: column;
          gap: 16px;
          padding: 8px 0;
        }
        .form-row {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        .form-row label {
          font-size: 12px;
          font-weight: 500;
          color: var(--secondary-text-color);
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
        .form-row select,
        .form-row input[type="text"],
        .form-row input[type="number"] {
          background: var(--card-background-color, #1c1c1c);
          border: 1px solid var(--divider-color, #444);
          border-radius: 4px;
          padding: 12px;
          font-size: 14px;
          color: var(--primary-text-color);
          width: 100%;
          box-sizing: border-box;
        }
        .form-row select:focus,
        .form-row input:focus {
          outline: none;
          border-color: var(--primary-color);
        }
        .form-row select {
          cursor: pointer;
        }
        .checkbox-row {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 8px 0;
        }
        .checkbox-row input[type="checkbox"] {
          width: 18px;
          height: 18px;
          cursor: pointer;
          accent-color: var(--primary-color);
        }
        .checkbox-row label {
          font-size: 14px;
          color: var(--primary-text-color);
          cursor: pointer;
          user-select: none;
        }
        .hint {
          font-size: 11px;
          color: var(--secondary-text-color);
          margin-top: 2px;
        }
      </style>
      
      <div class="editor-container">
        <div class="form-row">
          <label>Entity *</label>
          <select id="entity-select">
            <option value="">Select a feedparser entity...</option>
            ${entityOptions}
          </select>
          ${entities.length === 0 ? '<div class="hint">No feedparser entities found. Add a feed first.</div>' : ''}
        </div>

        <div class="form-row">
          <label>Title (optional)</label>
          <input type="text" id="title-input" value="${this._config.title || ''}" placeholder="Custom card title">
        </div>

        <div class="form-row">
          <label>Max entries</label>
          <input type="number" id="max-entries-input" value="${this._config.max_entries || ''}" placeholder="Default: 10" min="1" max="100">
        </div>

        <div class="checkbox-row">
          <input type="checkbox" id="show-images" ${this._config.show_images !== false ? 'checked' : ''}>
          <label for="show-images">Show images</label>
        </div>

        <div class="checkbox-row">
          <input type="checkbox" id="show-summary" ${this._config.show_summary !== false ? 'checked' : ''}>
          <label for="show-summary">Show summary</label>
        </div>

        <div class="checkbox-row">
          <input type="checkbox" id="show-date" ${this._config.show_date !== false ? 'checked' : ''}>
          <label for="show-date">Show date</label>
        </div>

        <div class="checkbox-row">
          <input type="checkbox" id="compact" ${this._config.compact === true ? 'checked' : ''}>
          <label for="compact">Compact mode</label>
        </div>

        <div class="checkbox-row">
          <input type="checkbox" id="show-refresh" ${this._config.show_refresh !== false ? 'checked' : ''}>
          <label for="show-refresh">Show refresh button</label>
        </div>
      </div>
    `;

    // Add event listeners
    this.querySelector('#entity-select').addEventListener('change', (e) => {
      this._updateConfig('entity', e.target.value);
    });

    this.querySelector('#title-input').addEventListener('input', (e) => {
      this._updateConfig('title', e.target.value);
    });

    this.querySelector('#max-entries-input').addEventListener('input', (e) => {
      const val = e.target.value ? parseInt(e.target.value, 10) : undefined;
      this._updateConfig('max_entries', val);
    });

    ['show-images', 'show-summary', 'show-date', 'compact', 'show-refresh'].forEach(id => {
      const key = id.replace(/-/g, '_');
      this.querySelector(`#${id}`).addEventListener('change', (e) => {
        this._updateConfig(key, e.target.checked);
      });
    });
  }

  _updateConfig(key, value) {
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
