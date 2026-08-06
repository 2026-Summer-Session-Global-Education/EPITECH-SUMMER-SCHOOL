const express = require('express');
const fs = require('fs'); // Node's built-in File System module
const cors = require('cors');

const app = express();
app.use(cors());
app.use(express.json()); // Allows the server to understand JSON bodies

const PORT = 3000;

// We will add our routes (GET, POST, etc.) here!

// GET: Retrieve all items
app.get('/api/inventory', (req, res) => {
  // 1. Read the file
  const rawData = fs.readFileSync('inventory.json');
  // 2. Convert it from text to a JavaScript array
  const inventory = JSON.parse(rawData);
  // 3. Send it back to the client
  res.status(200).json(inventory);
});

// POST: Add a new item
app.post('/api/inventory', (req, res) => {
  // 1. Get the current inventory
  const inventory = JSON.parse(fs.readFileSync('inventory.json'));
  // 2. Create the new item using the data sent by the client (req.body)
  const newItem = {
    id: Date.now(), // Generates a unique ID based on the current timestamp
    device: req.body.device,
    stock: req.body.stock
  };
  // 3. Push it to the array
  inventory.push(newItem);

  // 4. Save the updated array back to the JSON file
  fs.writeFileSync('inventory.json', JSON.stringify(inventory, null, 2));
  // 5. Respond to the client
  res.status(201).json({ message: "Item added!", item: newItem });
});

// PATCH: Update an item's stock
app.patch('/api/inventory/:id', (req, res) => {
  const inventory = JSON.parse(fs.readFileSync('inventory.json'));
  // Extract the ID from the URL (convert it to a number)
  const idToFind = parseInt(req.params.id);
  // Find the exact item in the array
  const item = inventory.find(i => i.id === idToFind);

  if (!item) {
    return res.status(404).json({ error: "Item not found" });
  }
  // Update the stock
  item.stock = req.body.stock;
  // Save the file
  fs.writeFileSync('inventory.json', JSON.stringify(inventory, null, 2));
  res.status(200).json({ message: "Stock updated!", item: item });
});

// DELETE: Remove an item
app.delete('/api/inventory/:id', (req, res) => {
  const inventory = JSON.parse(fs.readFileSync('inventory.json'));
  const idToDelete = parseInt(req.params.id);
  // Keep all items EXCEPT the one with the matching ID
  const newInventory = inventory.filter(i => i.id !== idToDelete);
  fs.writeFileSync('inventory.json', JSON.stringify(newInventory, null, 2));
  res.status(200).json({ message: "Item deleted!" });
});

app.listen(PORT, () => {
  console.log(`Server is running on http://localhost:${PORT}`);
});