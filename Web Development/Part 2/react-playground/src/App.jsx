// import './App.css';
import AlertButton from './components/AlertButton';

function App() {
  return (
    <div>
      <h1>Welcome to the React Sandbox</h1>
      <AlertButton text="Save Article" />
      <AlertButton text="Delete" />
      <AlertButton text="Publish Now" />
    </div>
  );
}

export default App;