# Breaking News Generator

A local web application that generates breaking news style images with customizable headlines, ticker text, and background images. Inspired by [breakyourownnews.com](https://breakyourownnews.com/).

## Features

- **Custom Headlines**: Add your own breaking news headline
- **Ticker Text**: Include scrolling ticker text at the bottom
- **Image Upload**: Upload your own background image
- **Multiple Sizes**: Choose from Wide Rectangle (1920x1080), Square (1080x1080), or Portrait (1080x1350)
- **Live Preview**: See your breaking news image update in real-time
- **Download**: Save your generated image as PNG

## Prerequisites

- Node.js (v16 or higher)
- npm or yarn

## Installation

1. Clone or navigate to this directory
2. Install dependencies:

```bash
npm install
```

## Development

To run the development server with hot-reload:

```bash
npm run dev
```

This will start the Vite development server on `http://localhost:5173`

## Production Build

To build for production:

```bash
npm run build
```

This creates an optimized production build in the `dist` directory.

## Running Production Server

After building, start the Express server:

```bash
npm run server
```

Or use the combined command:

```bash
npm start
```

The server will run on `http://localhost:3000` (or the port specified in the PORT environment variable).

## Usage

1. Enter your headline in the "Headline" field
2. (Optional) Add ticker text in the "Ticker" field
3. (Optional) Upload a background image
4. Select your desired image size
5. Preview your breaking news image
6. Click "Download your image" to save it

## Project Structure

```
breakingNews/
├── server.js                 # Express server
├── package.json              # Dependencies
├── vite.config.js           # Vite configuration
├── index.html               # HTML entry point
├── .gitignore
├── README.md
└── src/
    ├── main.jsx             # React entry point
    ├── App.jsx              # Main app component
    ├── App.css              # App styles
    ├── index.css            # Global styles
    ├── components/
    │   ├── NewsGenerator.jsx # Main generator component
    │   └── NewsGenerator.css # Component styles
    └── utils/
        └── canvasRenderer.js # Canvas rendering utilities
```

## Technology Stack

- **Frontend**: React 18
- **Build Tool**: Vite
- **Backend**: Express.js
- **Canvas API**: HTML5 Canvas for image generation

## Notes

- All image processing happens client-side - no images are uploaded to any server
- The app is intended for fun, humour and parody
- Be careful what you make and how it may be shared
- Avoid making things which are unlawful, defamatory or likely to cause distress

## License

This project is for educational and personal use.
