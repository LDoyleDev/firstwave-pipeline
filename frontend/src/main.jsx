import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App.jsx'
import { PasswordGate } from './PasswordGate.jsx'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 20000, retry: 2 },
  },
})

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <PasswordGate>
          <App />
        </PasswordGate>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
)
