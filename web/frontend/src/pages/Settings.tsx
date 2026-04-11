import { useState } from 'react'
import { Save, RefreshCw } from 'lucide-react'
import './Settings.css'

export default function SettingsPage() {
  const [settings, setSettings] = useState({
    agentCount: 4,
    maxRetries: 3,
    validationLevel: 'strict',
    memoryEnabled: true,
    skillAutoGenerate: true,
  })

  const handleSave = () => {
    console.log('Settings saved:', settings)
  }

  return (
    <div className="settings">
      <header className="page-header">
        <div className="header-left">
          <h2>Settings</h2>
          <p className="subtitle">Configure DarkFactory behavior</p>
        </div>
        <div className="header-actions">
          <button className="btn" onClick={handleSave}>
            <Save size={16} />
            Save Changes
          </button>
        </div>
      </header>

      <div className="settings-grid">
        <section className="settings-section">
          <h3>Agent Configuration</h3>

          <div className="setting-item">
            <label htmlFor="agentCount">Max Agent Count</label>
            <input
              type="number"
              id="agentCount"
              min="1"
              max="16"
              value={settings.agentCount}
              onChange={(e) => setSettings({ ...settings, agentCount: parseInt(e.target.value) })}
            />
          </div>

          <div className="setting-item">
            <label htmlFor="maxRetries">Max Retries</label>
            <input
              type="number"
              id="maxRetries"
              min="1"
              max="10"
              value={settings.maxRetries}
              onChange={(e) => setSettings({ ...settings, maxRetries: parseInt(e.target.value) })}
            />
          </div>
        </section>

        <section className="settings-section">
          <h3>Validation</h3>

          <div className="setting-item">
            <label htmlFor="validationLevel">Validation Level</label>
            <select
              id="validationLevel"
              value={settings.validationLevel}
              onChange={(e) => setSettings({ ...settings, validationLevel: e.target.value })}
            >
              <option value="relaxed">Relaxed</option>
              <option value="standard">Standard</option>
              <option value="strict">Strict</option>
            </select>
          </div>
        </section>

        <section className="settings-section">
          <h3>Memory & Skills</h3>

          <div className="setting-item toggle">
            <label htmlFor="memoryEnabled">Enable Memory System</label>
            <input
              type="checkbox"
              id="memoryEnabled"
              checked={settings.memoryEnabled}
              onChange={(e) => setSettings({ ...settings, memoryEnabled: e.target.checked })}
            />
          </div>

          <div className="setting-item toggle">
            <label htmlFor="skillAutoGenerate">Auto-generate Skills</label>
            <input
              type="checkbox"
              id="skillAutoGenerate"
              checked={settings.skillAutoGenerate}
              onChange={(e) => setSettings({ ...settings, skillAutoGenerate: e.target.checked })}
            />
          </div>
        </section>

        <section className="settings-section">
          <h3>System</h3>
          <div className="setting-item">
            <button className="btn">
              <RefreshCw size={16} />
              Reset to Defaults
            </button>
          </div>
        </section>
      </div>
    </div>
  )
}
