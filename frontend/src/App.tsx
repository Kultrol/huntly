import { Button } from "@/components/ui/button";
import { useState } from "react";

function App() {
  const products = [
    { title: "Cabbage", id: 1 },
    { title: "Garlic", id: 2 },
    { title: "Apple", id: 3 },
  ];

  const listItems = products.map((product) => (
    <li key={product.id} className="text-4xl text-red-600">
      {product.title}
    </li>
  ));

  return (
    <div>
      {listItems}
      <MyButton />
    </div>
  );
}

export default App;

function MyButton() {
  const [count, setCount] = useState(0);
  function handleClick() {
    setCount(count + 1);
  }

  return <button onClick={handleClick}>Clicked {count} times</button>;
}
