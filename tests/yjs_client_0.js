/*
 * Copyright (c) Jupyter Development Team.
 * Distributed under the terms of the Modified BSD License.
 */

import { YNotebook } from '@jupyter/ydoc'
import { WebsocketProvider } from 'y-websocket'

const port = process.argv[2]
const notebook = new YNotebook()
const ytest = notebook.ydoc.getMap('_test')
import ws from 'ws'

const wsProvider = new WebsocketProvider(
  `ws://127.0.0.1:${port}`, 'my-roomname',
  notebook.ydoc,
  { WebSocketPolyfill: ws }
)

wsProvider.on('status', event => {
  console.log(event.status)
})

var clock = -1

ytest.observe(event => {
  event.changes.keys.forEach((change, key) => {
    if (key === 'clock') {
      const clk = ytest.get('clock')
      if (clk > clock) {
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
        clock = clk + 1
        ytest.set('clock', clock)
      }
    }
  })
})
