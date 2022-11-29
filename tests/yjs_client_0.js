import { YNotebook } from '@jupyter/ydoc'
import { WebsocketProvider } from 'y-websocket'

const notebook = new YNotebook()
const ytest = notebook.ydoc.getMap('_test')
import ws from 'ws'

const wsProvider = new WebsocketProvider(
  'ws://localhost:1234', 'my-roomname',
  notebook.ydoc,
  { WebSocketPolyfill: ws }
)

wsProvider.on('status', event => {
  console.log(event.status)
})

ytest.observe(event => {
  event.changes.keys.forEach((change, key) => {
    if (key === 'clock') {
      const clock = ytest.get('clock')
      if (clock === 0) {
        const cells = []
        for (let cell of notebook.cells) {
          cells.push(cell.toJSON())
        }
        const metadata = notebook.getMetadata()
        const nbformat = notebook.nbformat
        const nbformat_minor = notebook.nbformat_minor
        const source = {
          cells,
          metadata,
          nbformat,
          nbformat_minor
        }
        ytest.set('source', source)
        ytest.set('clock', 1)
      }
    }
  })
})
