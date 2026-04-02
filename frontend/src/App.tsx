import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Suppliers from './pages/Suppliers'
import Alerts from './pages/Alerts'
import Agent from './pages/Agent'
import Reports from './pages/Reports'
import Pipeline from './pages/Pipeline'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/suppliers" element={<Suppliers />} />
        <Route path="/alerts" element={<Alerts />} />
        <Route path="/agent" element={<Agent />} />
        <Route path="/reports" element={<Reports />} />
        <Route path="/pipeline" element={<Pipeline />} />
      </Routes>
    </Layout>
  )
}

export default App
