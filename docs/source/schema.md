# Schemas

Yjs is untyped. We must know what each attribute contains at build-time and cast its values when accessing them. It is essential to ensure both models use the same schema, to prevent errors at run-time because of a wrong cast. For this purpose, in the following sections, we can find the description of the schema used by each model in case we want to extend them to create a custom model.

## YFile

```typescript
{
	/**
	 * Contains the state of the document.
	 * At the moment the only mandatory attributes are path and dirty.
	*/
	"state": YMap<string, any>,
	/**
	 * Contains the content of the document.
	*/
	"source": YText

}
```

### state:
```typescript
{
	/**
	 * Whether the document is dirty.
	*/
	"dirty": bool,
	/**
	 * Document's path.
	*/
	"path": str
}
```

## YNotebook

```typescript
{
	/**
	 * Contains the state of the document.
	 * At the moment the only mandatory attributes are path and dirty.
	*/
	"state": YMap<string, any>,
	/**
	 * Contains document's metadata.
	 *
	 * Note: Do not confuse it with the notebook's metadata attribute,
	 * "meta" has `nbformat`, `nbformat_minor`, and `metadata`
	*/
	"meta": YMap<string, any>,
	/**
	 * The list of YMap that stores the data of each cell.
	*/
	"cells": YArray<YMap<string, any>>
}
```

### state:
```typescript
{
	/**
	 * Whether the document is dirty.
	*/
	"dirty": bool,
	/**
	 * Document's path.
	*/
	"path": str
}
```

### meta:
```typescript
{
	/**
	 * The version of the notebook format supported by the schema.
	*/
	"nbformat": number,
	/**
	 * The minor version of the notebook format.
	*/
	"nbformat_minor": number,
	/**
	 * Notebook's metadata.
	*/
	"metadata": YMap<string, any>
}
```

### cells
```typescript
[
	/**
	 * The following JSON object is actually a YMap that contains
	 * the described attributes.
	*/
	{
		/**
		 * Cell's id.
		*/
		"id": str,
		/**
		 * Cell type.
		*/
		"cell_type": str,
		/**
		 * The content of the cell (the code).
		*/
		"source": YText,
		/**
		 * Cell's metadata.
		*/
		"metadata": YMap<string, any>,
		/**
		 * The execution count.
		*/
		"execution_count": Int | None,
		/**
		 * Cell's outputs.
		*/
		"outputs": [] | None,
		/**
		 * Cell's attachments.
		*/
		"attachments": {} | None
	}
]
```
