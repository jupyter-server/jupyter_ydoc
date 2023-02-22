/* eslint-disable camelcase */
// Copyright (c) Jupyter Development Team.
// Distributed under the terms of the Modified BSD License.

import { IMapChange, YCodeCell, YNotebook } from '../src';

describe('@jupyter/ydoc', () => {
  describe('YCell standalone', () => {
    test('should set source', () => {
      const codeCell = YCodeCell.createStandalone();
      codeCell.setSource('test');
      expect(codeCell.getSource()).toBe('test');
      codeCell.dispose();
    });

    test('should update source', () => {
      const codeCell = YCodeCell.createStandalone();
      codeCell.setSource('test');
      codeCell.updateSource(0, 0, 'hello');
      expect(codeCell.getSource()).toBe('hellotest');
      codeCell.dispose();
    });

    test('should get metadata', () => {
      const cell = YCodeCell.createStandalone();
      const metadata = {
        collapsed: true,
        editable: false,
        name: 'cell-name'
      };

      cell.setMetadata(metadata);

      expect(cell.metadata).toEqual({
        ...metadata,
        jupyter: { outputs_hidden: true }
      });
      cell.dispose();
    });

    test('should get all metadata', () => {
      const cell = YCodeCell.createStandalone();
      const metadata = {
        jupyter: { outputs_hidden: true },
        editable: false,
        name: 'cell-name'
      };

      cell.setMetadata(metadata);

      expect(cell.getMetadata()).toEqual({ ...metadata, collapsed: true });
      cell.dispose();
    });

    test('should get one metadata', () => {
      const cell = YCodeCell.createStandalone();
      const metadata = {
        collapsed: true,
        editable: false,
        name: 'cell-name'
      };

      cell.setMetadata(metadata);

      expect(cell.getMetadata('editable')).toEqual(metadata.editable);
      cell.dispose();
    });

    it.each([null, undefined, 1, true, 'string', { a: 1 }, [1, 2]])(
      'should get single metadata %s',
      value => {
        const cell = YCodeCell.createStandalone();
        const metadata = {
          collapsed: true,
          editable: false,
          name: 'cell-name',
          test: value
        };

        cell.setMetadata(metadata);

        expect(cell.getMetadata('test')).toEqual(value);
        cell.dispose();
      }
    );

    test('should set one metadata', () => {
      const cell = YCodeCell.createStandalone();
      const metadata = {
        collapsed: true,
        editable: false,
        name: 'cell-name'
      };

      cell.setMetadata(metadata);
      cell.setMetadata('test', 'banana');

      expect(cell.getMetadata('test')).toEqual('banana');
      cell.dispose();
    });

    test('should emit all metadata changes', () => {
      const notebook = YNotebook();

      const metadata = {
        collapsed: true,
        editable: false,
        name: 'cell-name'
      };

      const changes: IMapChange[] = [];
      notebook.metadataChanged.connect((_: any, c: any) => {
        changes.push(c);
      });
      notebook.metadata = metadata;

      expect(changes).toHaveLength(3);
      expect(changes).toEqual([
        {
          type: 'add',
          key: 'collapsed',
          newValue: metadata.collapsed,
          oldValue: undefined
        },
        {
          type: 'add',
          key: 'editable',
          newValue: metadata.editable,
          oldValue: undefined
        },
        {
          type: 'add',
          key: 'name',
          newValue: metadata.name,
          oldValue: undefined
        }
      ]);

      notebook.dispose();
    });

    test('should emit a add metadata change', () => {
      const cell = YCodeCell.createStandalone();
      const metadata = {
        collapsed: true,
        editable: false,
        name: 'cell-name'
      };
      cell.metadata = metadata;

      const changes: IMapChange[] = [];
      cell.metadataChanged.connect((_: any, c: any) => {
        changes.push(c);
      });
      cell.setMetadata('test', 'banana');

      try {
        expect(changes).toHaveLength(1);
        expect(changes).toEqual([
          { type: 'add', key: 'test', newValue: 'banana', oldValue: undefined }
        ]);
      } finally {
        cell.dispose();
      }
    });

    test('should emit a delete metadata change', () => {
      const cell = YCodeCell.createStandalone();
      const metadata = {
        collapsed: true,
        editable: false,
        name: 'cell-name'
      };
      cell.metadata = metadata;

      const changes: IMapChange[] = [];
      cell.setMetadata('test', 'banana');

      cell.metadataChanged.connect((_: any, c: any) => {
        changes.push(c);
      });
      cell.deleteMetadata('test');

      try {
        expect(changes).toHaveLength(1);
        expect(changes).toEqual([
          {
            type: 'remove',
            key: 'test',
            newValue: undefined,
            oldValue: 'banana'
          }
        ]);
      } finally {
        cell.dispose();
      }
    });

    test('should emit an update metadata change', () => {
      const cell = YCodeCell.createStandalone();
      const metadata = {
        collapsed: true,
        editable: false,
        name: 'cell-name'
      };
      cell.metadata = metadata;

      const changes: IMapChange[] = [];
      cell.setMetadata('test', 'banana');

      cell.metadataChanged.connect((_: any, c: any) => {
        changes.push(c);
      });
      cell.setMetadata('test', 'orange');

      try {
        expect(changes).toHaveLength(1);
        expect(changes).toEqual([
          {
            type: 'change',
            key: 'test',
            newValue: 'orange',
            oldValue: 'banana'
          }
        ]);
      } finally {
        cell.dispose();
      }
    });
  });

  describe('#undo', () => {
    test('should undo source change', () => {
      const codeCell = YCodeCell.createStandalone();
      codeCell.setSource('test');
      codeCell.undoManager?.stopCapturing();
      codeCell.updateSource(0, 0, 'hello');

      codeCell.undo();

      expect(codeCell.getSource()).toEqual('test');
    });

    test('should not undo execution count change', () => {
      const codeCell = YCodeCell.createStandalone();
      codeCell.setSource('test');
      codeCell.undoManager?.stopCapturing();
      codeCell.execution_count = 22;
      codeCell.undoManager?.stopCapturing();
      codeCell.execution_count = 42;

      codeCell.undo();

      expect(codeCell.execution_count).toEqual(42);
    });

    test('should not undo output change', () => {
      const codeCell = YCodeCell.createStandalone();
      codeCell.setSource('test');
      codeCell.undoManager?.stopCapturing();
      const outputs = [
        {
          data: {
            'application/geo+json': {
              geometry: {
                coordinates: [-118.4563712, 34.0163116],
                type: 'Point'
              },
              type: 'Feature'
            },
            'text/plain': ['<IPython.display.GeoJSON object>']
          },
          metadata: {
            'application/geo+json': {
              expanded: false
            }
          },
          output_type: 'display_data'
        },
        {
          data: {
            'application/vnd.jupyter.widget-view+json': {
              model_id: '4619c172d65e496baa5d1230894b535a',
              version_major: 2,
              version_minor: 0
            },
            'text/plain': [
              "HBox(children=(Text(value='text input', layout=Layout(border='1px dashed red', width='80px')), Button(descript…"
            ]
          },
          metadata: {},
          output_type: 'display_data'
        }
      ];
      codeCell.setOutputs(outputs);
      codeCell.undoManager?.stopCapturing();

      codeCell.undo();

      expect(codeCell.getOutputs()).toEqual(outputs);
    });

    test('should not undo metadata change', () => {
      const codeCell = YCodeCell.createStandalone();
      codeCell.setSource('test');
      codeCell.undoManager?.stopCapturing();
      codeCell.setMetadata({ collapsed: false });
      codeCell.undoManager?.stopCapturing();
      codeCell.setMetadata({ collapsed: true });

      codeCell.undo();

      expect(codeCell.getMetadata('collapsed')).toEqual(true);
    });
  });
});
