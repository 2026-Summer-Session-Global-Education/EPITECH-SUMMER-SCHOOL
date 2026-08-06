import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from './assets/vite.svg'
import heroImg from './assets/hero.png'
import './App.css'

function App() {
  const [count, setCount] = useState(0)
  const [text, setText] = useState('')
  // 1. Create a Boolean state (starts false)
  const [isOn, setIsOn] = useState(false)

  return (
    <>
      <h1>Vite + React</h1>
      <div className="card">
        <button onClick={() => setCount((count) => count + 1)}>
          count is {count}
        </button>

        <div style={{ marginTop: '20px' }}>
          <input
            type="text"
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <p>
            You are typing: <i>{text}</i>
          </p>
        </div>

        {/* 2. Our New Toggle Switch */}
        <div
          style={{
            marginTop: '20px',
            padding: '10px',
            border: '1px solid gray',
          }}
        >
          <h3>The system is currently: {isOn ? 'ONLINE' : 'OFFLINE'}</h3>
          {/* The ! operator means "Not". It flips true to false, and false to true. */}
          <button onClick={() => setIsOn(!isOn)}>
            Toggle System
          </button>
        </div>
      </div>
    </>
  )
}

export default App
