/* eslint-disable @typescript-eslint/no-this-alias */
/* eslint-disable @typescript-eslint/explicit-module-boundary-types */
/* eslint-disable @typescript-eslint/no-explicit-any */

class FeedParserCard extends HTMLElement {
  constructor() {
    super();
    this._lastEntriesHash = null;
  }

  setConfig(config) {
    this.config = config;
    if (!this.config.entity) {
      throw new Error('Entity is required');
    }
  }

  set hass(hass) {
    this._hass = hass;
    
    if (this.config && this.config.entity) {
      const entityId = this.config.entity;
      const newState = hass.states[entityId];
      
      const newEntriesHash = newState ? JSON.stringify({
        state: newState.state,
        entries: newState.attributes.entries,
        feed_title: newState.attributes.feed_title,
        last_entry_date: newState.attributes.last_entry_date
      }) : null;
      
      if (newEntriesHash !== this._lastEntriesHash) {
        this._lastEntriesHash = newEntriesHash;
        this.updateCard();
      }
    } else {
      this.updateCard();
    }
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

  getGridOptions() {
    return {
      columns: 12,
      rows: 3,
      min_columns: 6,
      min_rows: 2,
    };
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

class FeedParserCardEditor extends HTMLElement {
  constructor() {
    super();
    this._config = {};
    this._hass = null;
    this._initialized = false;
  }

  setConfig(config) {
    this._config = { ...config };
    if (!this._initialized) {
      this._render();
    } else {
      this._updateValues();
    }
  }

  set hass(hass) {
    const hadHass = !!this._hass;
    this._hass = hass;
    
    if (!hadHass && hass) {
      this._render();
    }
  }

  get hass() {
    return this._hass;
  }

  _updateValues() {
    const entityPicker = this.querySelector('ha-entity-picker#entity-picker');
    const fallbackSelect = this.querySelector('select#entity-select');
    
    if (entityPicker && entityPicker.value !== this._config.entity) {
      entityPicker.value = this._config.entity || '';
    } else if (fallbackSelect && fallbackSelect.value !== this._config.entity) {
      fallbackSelect.value = this._config.entity || '';
    }
    
    const titleInput = this.querySelector('#title-input');
    if (titleInput && titleInput.value !== (this._config.title || '')) {
      titleInput.value = this._config.title || '';
    }
    
    const maxEntriesInput = this.querySelector('#max-entries-input');
    if (maxEntriesInput) {
      const configVal = this._config.max_entries || '';
      if (maxEntriesInput.value !== String(configVal)) {
        maxEntriesInput.value = configVal;
      }
    }
  }

  _render() {
    if (!this._hass) {
      return;
    }

    this._initialized = true;

    this.innerHTML = `
      <style>
        .editor-container {
          display: flex;
          flex-direction: column;
          gap: 24px;
        }
        .form-row {
          display: flex;
          flex-direction: column;
        }
        ha-entity-picker {
          display: block;
          width: 100%;
        }
        ha-textfield {
          display: block;
          width: 100%;
        }
        ha-formfield {
          display: flex;
          align-items: center;
          padding: 4px 0;
        }
        .switches-section {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        .section-title {
          font-size: 12px;
          font-weight: 500;
          color: var(--secondary-text-color);
          text-transform: uppercase;
          letter-spacing: 0.5px;
          margin-bottom: 8px;
        }
      </style>
      
      <div class="editor-container">
        <div class="form-row" id="entity-picker-container"></div>

        <div class="form-row">
          <ha-textfield
            id="title-input"
            label="Title (optional)"
            placeholder="Custom card title"
          ></ha-textfield>
        </div>

        <div class="form-row">
          <ha-textfield
            id="max-entries-input"
            label="Max entries"
            placeholder="Leave empty for all"
            type="number"
            min="1"
            max="100"
          ></ha-textfield>
        </div>

        <div class="switches-section">
          <div class="section-title">Display Options</div>
          
          <ha-formfield label="Show images">
            <ha-switch id="show-images"></ha-switch>
          </ha-formfield>

          <ha-formfield label="Show summary">
            <ha-switch id="show-summary"></ha-switch>
          </ha-formfield>

          <ha-formfield label="Show date">
            <ha-switch id="show-date"></ha-switch>
          </ha-formfield>

          <ha-formfield label="Compact mode">
            <ha-switch id="compact"></ha-switch>
          </ha-formfield>

          <ha-formfield label="Show refresh button">
            <ha-switch id="show-refresh"></ha-switch>
          </ha-formfield>
        </div>
      </div>
    `;

    const entityPickerContainer = this.querySelector('#entity-picker-container');
    if (entityPickerContainer) {
      this._initEntityPicker(entityPickerContainer);
    }

    const titleInput = this.querySelector('#title-input');
    if (titleInput) {
      titleInput.value = this._config.title || '';
      titleInput.addEventListener('input', (ev) => {
        this._updateConfig('title', ev.target.value);
      });
    }

    const maxEntriesInput = this.querySelector('#max-entries-input');
    if (maxEntriesInput) {
      maxEntriesInput.value = this._config.max_entries || '';
      maxEntriesInput.addEventListener('input', (ev) => {
        const val = ev.target.value ? parseInt(ev.target.value, 10) : undefined;
        this._updateConfig('max_entries', val);
      });
    }

    const switchConfigs = [
      { id: 'show-images', key: 'show_images', defaultValue: true },
      { id: 'show-summary', key: 'show_summary', defaultValue: true },
      { id: 'show-date', key: 'show_date', defaultValue: true },
      { id: 'compact', key: 'compact', defaultValue: false },
      { id: 'show-refresh', key: 'show_refresh', defaultValue: true },
    ];

    switchConfigs.forEach(({ id, key, defaultValue }) => {
      const switchEl = this.querySelector(`#${id}`);
      if (switchEl) {
        const currentValue = this._config[key];
        switchEl.checked = currentValue !== undefined ? currentValue : defaultValue;
        
        switchEl.addEventListener('change', (ev) => {
          this._updateConfig(key, ev.target.checked);
        });
      }
    });
  }

  async _initEntityPicker(container) {
    let isEntityPickerDefined = customElements.get('ha-entity-picker');
    
    if (!isEntityPickerDefined) {
      try {
        await Promise.race([
          customElements.whenDefined('ha-entity-picker'),
          new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), 5000))
        ]);
        isEntityPickerDefined = true;
      } catch {
        isEntityPickerDefined = false;
      }
    }
    
    if (isEntityPickerDefined) {
      this._createEntityPicker(container);
    } else {
      this._createFallbackEntityPicker(container);
    }
  }

  _createEntityPicker(container) {
    const existingPicker = container.querySelector('#entity-picker');
    if (existingPicker) {
      existingPicker.remove();
    }
    
    try {
      const entityPicker = document.createElement('ha-entity-picker');
      entityPicker.id = 'entity-picker';
      entityPicker.hass = this._hass;
      entityPicker.value = this._config.entity || '';
      entityPicker.label = 'Entity (Required)';
      entityPicker.includeDomains = ['sensor'];
      entityPicker.allowCustomEntity = true;
      
      entityPicker.entityFilter = (stateObj) => {
        return stateObj.attributes && stateObj.attributes.entries !== undefined;
      };
      
      entityPicker.addEventListener('value-changed', (ev) => {
        if (ev.detail && ev.detail.value !== undefined) {
          this._updateConfig('entity', ev.detail.value);
        }
      });
      
      container.appendChild(entityPicker);
    } catch {
      this._createFallbackEntityPicker(container);
    }
  }

  _createFallbackEntityPicker(container) {
    const existingPicker = container.querySelector('#entity-picker');
    if (existingPicker) {
      existingPicker.remove();
    }
    
    const wrapper = document.createElement('div');
    wrapper.id = 'entity-picker';
    wrapper.innerHTML = `
      <label style="display: block; font-size: 12px; color: var(--secondary-text-color); margin-bottom: 4px;">
        Entity (Required)
      </label>
      <select id="entity-select" style="width: 100%; padding: 8px; border-radius: 4px; border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color);">
        <option value="">Select a feedparser entity...</option>
      </select>
    `;
    
    container.appendChild(wrapper);
    
    const select = wrapper.querySelector('#entity-select');
    
    if (this._hass && this._hass.states) {
      Object.keys(this._hass.states)
        .filter(entityId => {
          const state = this._hass.states[entityId];
          return entityId.startsWith('sensor.') && 
                 state.attributes && 
                 state.attributes.entries !== undefined;
        })
        .forEach(entityId => {
          const option = document.createElement('option');
          option.value = entityId;
          option.textContent = this._hass.states[entityId].attributes.friendly_name || entityId;
          if (entityId === this._config.entity) {
            option.selected = true;
          }
          select.appendChild(option);
        });
    }
    
    select.addEventListener('change', (ev) => {
      this._updateConfig('entity', ev.target.value);
    });
  }

  _updateConfig(key, value) {
    const newConfig = { ...this._config };
    
    if (value === '' || value === undefined || value === null) {
      if (key === 'entity') {
        newConfig[key] = '';
      } else {
        delete newConfig[key];
      }
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

window.customCards = window.customCards || [];
window.customCards.push({
  type: 'feedparser-card',
  name: 'Feedparser Card',
  description: 'Display RSS/Atom feed entries in a beautiful card',
  preview: true,
  documentationURL: 'https://github.com/custom-components/feedparser'
});
