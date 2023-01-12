// Copyright (c) Jupyter Development Team.
// Distributed under the terms of the Modified BSD License.

import { IMapChange, NotebookChange, YCodeCell, YNotebook } from '../src';

describe('@jupyter/ydoc', () => {
  describe('YNotebook', () => {
    describe('#constructor', () => {
      test('should create a notebook without arguments', () => {
        const notebook = YNotebook.create();
        expect(notebook.cells.length).toBe(0);
        notebook.dispose();
      });
    });

    describe('#disposed', () => {
      test('should be emitted when the document is disposed', () => {
        const notebook = YNotebook.create();
        let disposed = false;
        notebook.disposed.connect(() => {
          disposed = true;
        });
        notebook.dispose();
        expect(disposed).toEqual(true);
      });
    });

    describe('metadata', () => {
      test('should get metadata', () => {
        const notebook = YNotebook.create();
        const metadata = {
          orig_nbformat: 1,
          kernelspec: {
            display_name: 'python',
            name: 'python'
          }
        };

        notebook.setMetadata(metadata);

        expect(notebook.metadata).toEqual(metadata);
        notebook.dispose();
      });

      test('should get all metadata', () => {
        const notebook = YNotebook.create();
        const metadata = {
          orig_nbformat: 1,
          kernelspec: {
            display_name: 'python',
            name: 'python'
          }
        };

        notebook.setMetadata(metadata);

        expect(notebook.getMetadata()).toEqual(metadata);
        notebook.dispose();
      });

      test('should get one metadata', () => {
        const notebook = YNotebook.create();
        const metadata = {
          orig_nbformat: 1,
          kernelspec: {
            display_name: 'python',
            name: 'python'
          }
        };

        notebook.setMetadata(metadata);

        expect(notebook.getMetadata('orig_nbformat')).toEqual(1);
        notebook.dispose();
      });

      test('should set one metadata', () => {
        const notebook = YNotebook.create();
        const metadata = {
          orig_nbformat: 1,
          kernelspec: {
            display_name: 'python',
            name: 'python'
          }
        };

        notebook.setMetadata(metadata);
        notebook.setMetadata('test', 'banana');

        expect(notebook.getMetadata('test')).toEqual('banana');
        notebook.dispose();
      });

      it.each([null, undefined, 1, true, 'string', { a: 1 }, [1, 2]])(
        'should get single metadata %s',
        value => {
          const nb = YNotebook.create();
          const metadata = {
            orig_nbformat: 1,
            kernelspec: {
              display_name: 'python',
              name: 'python'
            },
            test: value
          };

          nb.setMetadata(metadata);

          expect(nb.getMetadata('test')).toEqual(value);
          nb.dispose();
        }
      );

      test('should update metadata', () => {
        const notebook = YNotebook.create();
        const metadata = notebook.getMetadata();
        expect(metadata).toBeTruthy();
        metadata.orig_nbformat = 1;
        metadata.kernelspec = {
          display_name: 'python',
          name: 'python'
        };
        notebook.setMetadata(metadata);
        {
          const metadata = notebook.getMetadata();
          expect(metadata.kernelspec!.name).toBe('python');
          expect(metadata.orig_nbformat).toBe(1);
        }
        notebook.updateMetadata({
          orig_nbformat: 2
        });
        {
          const metadata = notebook.getMetadata();
          expect(metadata.kernelspec!.name).toBe('python');
          expect(metadata.orig_nbformat).toBe(2);
        }
        notebook.dispose();
      });

      test('should emit all metadata changes', () => {
        const notebook = YNotebook.create();

        const metadata = {
          orig_nbformat: 1,
          kernelspec: {
            display_name: 'python',
            name: 'python'
          }
        };

        const changes: IMapChange[] = [];
        notebook.metadataChanged.connect((_, c) => {
          changes.push(c);
        });
        notebook.metadata = metadata;

        expect(changes).toHaveLength(3);
        expect(changes).toEqual([
          {
            type: 'remove',
            key: 'language_info',
            oldValue: { name: '' }
          },
          {
            type: 'change',
            key: 'kernelspec',
            newValue: metadata.kernelspec,
            oldValue: { display_name: '', name: '' }
          },
          {
            type: 'add',
            key: 'orig_nbformat',
            newValue: metadata.orig_nbformat
          }
        ]);

        notebook.dispose();
      });

      test('should emit all metadata changes on update', () => {
        const notebook = YNotebook.create();

        const metadata = {
          orig_nbformat: 1,
          kernelspec: {
            display_name: 'python',
            name: 'python'
          }
        };

        const changes: IMapChange[] = [];
        notebook.metadataChanged.connect((_, c) => {
          changes.push(c);
        });
        notebook.updateMetadata(metadata);

        expect(changes).toHaveLength(2);
        expect(changes).toEqual([
          {
            type: 'add',
            key: 'orig_nbformat',
            newValue: metadata.orig_nbformat
          },
          {
            type: 'change',
            key: 'kernelspec',
            newValue: metadata.kernelspec,
            oldValue: { display_name: '', name: '' }
          }
        ]);

        notebook.dispose();
      });

      test('should emit a add metadata change', () => {
        const notebook = YNotebook.create();
        const metadata = {
          orig_nbformat: 1,
          kernelspec: {
            display_name: 'python',
            name: 'python'
          }
        };
        notebook.metadata = metadata;

        const changes: IMapChange[] = [];
        notebook.metadataChanged.connect((_, c) => {
          changes.push(c);
        });
        notebook.setMetadata('test', 'banana');

        expect(changes).toHaveLength(1);
        expect(changes).toEqual([
          { type: 'add', key: 'test', newValue: 'banana', oldValue: undefined }
        ]);

        notebook.dispose();
      });

      test('should emit a delete metadata change', () => {
        const notebook = YNotebook.create();
        const metadata = {
          orig_nbformat: 1,
          kernelspec: {
            display_name: 'python',
            name: 'python'
          }
        };
        notebook.metadata = metadata;

        const changes: IMapChange[] = [];
        notebook.setMetadata('test', 'banana');

        notebook.metadataChanged.connect((_, c) => {
          changes.push(c);
        });
        notebook.deleteMetadata('test');

        expect(changes).toHaveLength(1);
        expect(changes).toEqual([
          {
            type: 'remove',
            key: 'test',
            newValue: undefined,
            oldValue: 'banana'
          }
        ]);

        notebook.dispose();
      });

      test('should emit an update metadata change', () => {
        const notebook = YNotebook.create();
        const metadata = {
          orig_nbformat: 1,
          kernelspec: {
            display_name: 'python',
            name: 'python'
          }
        };
        notebook.metadata = metadata;

        const changes: IMapChange[] = [];
        notebook.setMetadata('test', 'banana');

        notebook.metadataChanged.connect((_, c) => {
          changes.push(c);
        });
        notebook.setMetadata('test', 'orange');

        expect(changes).toHaveLength(1);
        expect(changes).toEqual([
          {
            type: 'change',
            key: 'test',
            newValue: 'orange',
            oldValue: 'banana'
          }
        ]);

        notebook.dispose();
      });
    });

    describe('#insertCell', () => {
      test('should insert a cell', () => {
        const notebook = YNotebook.create();
        notebook.insertCell(0, { cell_type: 'code' });
        expect(notebook.cells.length).toBe(1);
        notebook.dispose();
      });
      test('should set cell source', () => {
        const notebook = YNotebook.create();
        const codeCell = notebook.insertCell(0, { cell_type: 'code' });
        codeCell.setSource('test');
        expect(notebook.cells[0].getSource()).toBe('test');
        notebook.dispose();
      });
      test('should update source', () => {
        const notebook = YNotebook.create();
        const codeCell = notebook.insertCell(0, { cell_type: 'code' });
        codeCell.setSource('test');
        codeCell.updateSource(0, 0, 'hello');
        expect(codeCell.getSource()).toBe('hellotest');
        notebook.dispose();
      });

      test('should emit a add cells change', () => {
        const notebook = YNotebook.create();
        const changes: NotebookChange[] = [];
        notebook.changed.connect((_, c) => {
          changes.push(c);
        });
        const codeCell = notebook.insertCell(0, { cell_type: 'code' });

        expect(changes).toHaveLength(1);
        expect(changes[0].cellsChange).toEqual([
          {
            insert: [codeCell]
          }
        ]);
        notebook.dispose();
      });
    });

    describe('#deleteCell', () => {
      test('should emit a delete cells change', () => {
        const notebook = YNotebook.create();
        const changes: NotebookChange[] = [];
        const codeCell = notebook.insertCell(0, { cell_type: 'code' });

        notebook.changed.connect((_, c) => {
          changes.push(c);
        });
        notebook.deleteCell(0);

        expect(changes).toHaveLength(1);
        expect(codeCell.isDisposed).toEqual(true);
        expect(changes[0].cellsChange).toEqual([{ delete: 1 }]);
        notebook.dispose();
      });
    });

    describe('#moveCell', () => {
      test('should emit add and delete cells changes when moving a cell', () => {
        const notebook = YNotebook.create();
        const changes: NotebookChange[] = [];
        const codeCell = notebook.addCell({ cell_type: 'code' });
        notebook.addCell({ cell_type: 'markdown' });
        const raw = codeCell.toJSON();
        notebook.changed.connect((_, c) => {
          changes.push(c);
        });
        notebook.moveCell(0, 1);

        expect(notebook.getCell(1)).not.toEqual(codeCell);
        expect(notebook.getCell(1).toJSON()).toEqual(raw);
        expect(changes[0].cellsChange).toHaveLength(3);
        expect(changes[0].cellsChange).toEqual([
          { delete: 1 },
          { retain: 1 },
          {
            insert: [notebook.getCell(1)]
          }
        ]);
        notebook.dispose();
      });
    });

    describe('#fromJSON', () => {
      test('should load a serialize notebook', () => {
        const notebook = YNotebook.create();
        notebook.fromJSON({
          cells: [],
          metadata: {
            dummy: 42
          },
          nbformat: 4,
          nbformat_minor: 5
        });

        expect(notebook.cells).toHaveLength(0);
        expect(notebook.nbformat).toEqual(4);
        expect(notebook.nbformat_minor).toEqual(5);
        notebook.dispose();
      });

      test('should remove orig_nbformat', () => {
        const notebook = YNotebook.create();
        notebook.fromJSON({
          cells: [],
          metadata: {
            dummy: 42,
            orig_nbformat: 3
          },
          nbformat: 4,
          nbformat_minor: 5
        });

        expect(notebook.getMetadata('orig_nbformat')).toEqual(undefined);
        notebook.dispose();
      });

      test('should remove cell id for version <4.5', () => {
        const notebook = YNotebook.create();
        notebook.fromJSON({
          cells: [
            {
              cell_type: 'code',
              id: 'first-cell',
              source: '',
              metadata: {}
            }
          ],
          metadata: {
            dummy: 42
          },
          nbformat: 4,
          nbformat_minor: 4
        });

        expect(notebook.cells).toHaveLength(1);
        expect(notebook.cells[0].id).not.toEqual('first-cell');
        notebook.dispose();
      });
    });
  });

  describe('YCell standalone', () => {
    test('should set source', () => {
      const codeCell = YCodeCell.create();
      codeCell.setSource('test');
      expect(codeCell.getSource()).toBe('test');
      codeCell.dispose();
    });

    test('should update source', () => {
      const codeCell = YCodeCell.create();
      codeCell.setSource('test');
      codeCell.updateSource(0, 0, 'hello');
      expect(codeCell.getSource()).toBe('hellotest');
      codeCell.dispose();
    });

    test('should get metadata', () => {
      const cell = YCodeCell.create();
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
      const cell = YCodeCell.create();
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
      const cell = YCodeCell.create();
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
        const cell = YCodeCell.create();
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
      const cell = YCodeCell.create();
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
      const notebook = YNotebook.create();

      const metadata = {
        collapsed: true,
        editable: false,
        name: 'cell-name'
      };

      const changes: IMapChange[] = [];
      notebook.metadataChanged.connect((_, c) => {
        changes.push(c);
      });
      notebook.metadata = metadata;

      expect(changes).toHaveLength(5);
      expect(changes).toEqual([
        {
          type: 'remove',
          key: 'language_info',
          newValue: undefined,
          oldValue: { name: '' }
        },
        {
          type: 'remove',
          key: 'kernelspec',
          newValue: undefined,
          oldValue: { display_name: '', name: '' }
        },
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
      const cell = YCodeCell.create();
      const metadata = {
        collapsed: true,
        editable: false,
        name: 'cell-name'
      };
      cell.metadata = metadata;

      const changes: IMapChange[] = [];
      cell.metadataChanged.connect((_, c) => {
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
      const cell = YCodeCell.create();
      const metadata = {
        collapsed: true,
        editable: false,
        name: 'cell-name'
      };
      cell.metadata = metadata;

      const changes: IMapChange[] = [];
      cell.setMetadata('test', 'banana');

      cell.metadataChanged.connect((_, c) => {
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
      const cell = YCodeCell.create();
      const metadata = {
        collapsed: true,
        editable: false,
        name: 'cell-name'
      };
      cell.metadata = metadata;

      const changes: IMapChange[] = [];
      cell.setMetadata('test', 'banana');

      cell.metadataChanged.connect((_, c) => {
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
});
