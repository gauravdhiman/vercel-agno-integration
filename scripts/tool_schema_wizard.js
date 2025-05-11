#!/usr/bin/env node
/**
 * Frontend Tool Schema Wizard
 *
 * This script guides users through creating or updating frontend tool schemas.
 * It provides a step-by-step process to define tool names, parameters, and descriptions,
 * then updates the TypeScript definitions and generates the Python code.
 */

const fs = require('fs');
const path = require('path');
const readline = require('readline');
const { execSync } = require('child_process');

// Get the project root directory
const projectRoot = path.resolve(__dirname, '..');

// File paths
const tsFilePath = path.join(projectRoot, 'common', 'frontend_tools.ts');
const pyGeneratorPath = path.join(projectRoot, 'scripts', 'generate_frontend_tools_python.js');

// Create readline interface
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

// Helper function to ask questions
function askQuestion(question) {
  return new Promise((resolve) => {
    rl.question(question, (answer) => {
      resolve(answer);
    });
  });
}

// Helper function to validate required input
async function askRequiredQuestion(question) {
  let answer = '';
  while (!answer.trim()) {
    answer = await askQuestion(question);
    if (!answer.trim()) {
      console.log('This field is required. Please provide a value.');
    }
  }
  return answer;
}

// Helper function to ask yes/no questions
async function askYesNo(question) {
  const answer = await askQuestion(`${question} (y/n): `);
  return answer.toLowerCase().startsWith('y');
}

// Helper function to ask for a selection from a list
async function askSelection(question, options) {
  console.log(question);
  options.forEach((option, index) => {
    console.log(`${index + 1}. ${option}`);
  });

  let selection = -1;
  while (selection < 1 || selection > options.length) {
    const answer = await askQuestion(`Enter a number (1-${options.length}): `);
    selection = parseInt(answer);
    if (isNaN(selection) || selection < 1 || selection > options.length) {
      console.log(`Please enter a valid number between 1 and ${options.length}.`);
    }
  }

  return options[selection - 1];
}

// Helper function to parse TypeScript file
function parseTypeScriptFile() {
  try {
    const content = fs.readFileSync(tsFilePath, 'utf8');

    // Extract existing tool names from enum
    const enumMatch = content.match(/export enum FrontendToolName {([^}]*)}/s);
    const toolNames = [];

    if (enumMatch && enumMatch[1]) {
      const enumContent = enumMatch[1].trim();
      const lines = enumContent.split('\n');

      for (const line of lines) {
        const match = line.match(/\s*([A-Z_]+)\s*=\s*"([^"]+)"/);
        if (match) {
          toolNames.push({
            enumName: match[1],
            value: match[2]
          });
        }
      }
    }

    return { toolNames, content };
  } catch (error) {
    console.error('Error parsing TypeScript file:', error);
    return { toolNames: [], content: '' };
  }
}

// Helper function to convert string to UPPER_SNAKE_CASE
function toUpperSnakeCase(str) {
  return str
    .replace(/([a-z])([A-Z])/g, '$1_$2') // Convert camelCase to snake_case
    .replace(/[\s-]+/g, '_')             // Replace spaces and hyphens with underscores
    .toUpperCase();                      // Convert to uppercase
}

// Helper function to convert string to snake_case
function toSnakeCase(str) {
  return str
    .replace(/([a-z])([A-Z])/g, '$1_$2') // Convert camelCase to snake_case
    .replace(/[\s-]+/g, '_')             // Replace spaces and hyphens with underscores
    .toLowerCase();                      // Convert to lowercase
}

// Helper function to generate TypeScript parameter interface
function generateParameterInterface(toolName, parameters) {
  const interfaceName = `${toolName.charAt(0).toUpperCase() + toolName.slice(1)}Params`;

  let interfaceCode = `/**\n * Parameters for the ${toolName} tool\n */\nexport interface ${interfaceName} {\n`;

  for (const param of parameters) {
    interfaceCode += `  /** ${param.description} */\n`;
    interfaceCode += `  ${param.name}${param.required ? '' : '?'}: ${param.type};\n\n`;
  }

  interfaceCode += `}\n`;
  return interfaceCode;
}

// Helper function to generate JSON schema for parameters
function generateJsonSchema(parameters) {
  const schema = {
    type: 'object',
    properties: {},
    required: []
  };

  for (const param of parameters) {
    schema.properties[param.name] = {
      type: param.jsonType,
      description: param.description
    };

    if (param.required) {
      schema.required.push(param.name);
    }
  }

  return schema;
}

// Helper function to generate schema function
function generateSchemaFunction(enumName, toolName, description, parameters) {
  const jsonSchema = generateJsonSchema(parameters);

  let functionCode = `/**\n * Generate JSON Schema for the ${toolName} tool\n */\n`;
  functionCode += `function get${enumName}Schema(): FrontendToolSchema {\n`;
  functionCode += `  return {\n`;
  functionCode += `    name: FrontendToolName.${enumName},\n`;
  functionCode += `    description: "${description}",\n`;
  functionCode += `    parameters: ${JSON.stringify(jsonSchema, null, 4).replace(/"/g, '\\"').replace(/\\"/g, '"').replace(/\n/g, '\n    ')}\n`;
  functionCode += `  };\n`;
  functionCode += `}\n`;

  return functionCode;
}

// Helper function to update the getAllFrontendToolSchemas function
function updateGetAllFunction(content, enumName) {
  const getAllFunctionRegex = /export function getAllFrontendToolSchemas\(\): FrontendToolSchema\[\] {\s*return \[([\s\S]*?)\s*\];/;
  const match = content.match(getAllFunctionRegex);

  if (match) {
    const existingSchemas = match[1].trim();
    const updatedSchemas = existingSchemas ? `${existingSchemas},\n    get${enumName}Schema()` : `get${enumName}Schema()`;
    return content.replace(getAllFunctionRegex, `export function getAllFrontendToolSchemas(): FrontendToolSchema[] {\n  return [\n    ${updatedSchemas}\n  ];`);
  }

  return content;
}

// Main function to add a new tool
async function addNewTool() {
  console.log('\n=== Add New Frontend Tool ===\n');

  // Get tool name and description
  const toolDisplayName = await askRequiredQuestion('Enter the tool name (human-readable, e.g., "Display Product Card"): ');
  const toolName = toSnakeCase(toolDisplayName);
  const enumName = toUpperSnakeCase(toolDisplayName);

  const description = await askRequiredQuestion('Enter a description for the tool: ');

  // Get parameters
  const parameters = [];
  console.log('\nNow, let\'s define the parameters for this tool:');

  let addMoreParams = true;
  while (addMoreParams) {
    const paramName = await askRequiredQuestion('\nParameter name (camelCase): ');

    const typeOptions = ['string', 'number', 'boolean', 'object', 'array', 'string | number', 'string | boolean'];
    const paramType = await askSelection('Select the TypeScript type:', typeOptions);

    const jsonTypeOptions = ['string', 'number', 'boolean', 'object', 'array', ['string', 'number'], ['string', 'boolean']];
    const jsonTypeIndex = typeOptions.indexOf(paramType);
    const jsonType = jsonTypeOptions[jsonTypeIndex];

    const description = await askRequiredQuestion('Parameter description: ');
    const required = await askYesNo('Is this parameter required?');

    parameters.push({
      name: paramName,
      type: paramType,
      jsonType,
      description,
      required
    });

    addMoreParams = await askYesNo('Add another parameter?');
  }

  // Parse existing file
  const { toolNames, content } = parseTypeScriptFile();

  // Check if tool name already exists
  if (toolNames.some(tool => tool.enumName === enumName || tool.value === toolName)) {
    console.log(`\nWarning: A tool with the name "${toolName}" already exists.`);
    const overwrite = await askYesNo('Do you want to overwrite it?');
    if (!overwrite) {
      console.log('Operation cancelled.');
      return;
    }
  }

  // Generate new code
  const parameterInterface = generateParameterInterface(toolName, parameters);
  const schemaFunction = generateSchemaFunction(enumName, toolName, description, parameters);

  // These will be used later in the function

  // Update enum if needed
  let updatedContent = content;
  if (!toolNames.some(tool => tool.enumName === enumName)) {
    // Check if we need to add a comma to the previous entry
    const enumRegex = /(export enum FrontendToolName {[^}]*?)([\s\n]*})/s;
    const enumMatch = content.match(enumRegex);

    if (enumMatch) {
      const enumContent = enumMatch[1];

      // Find the last entry in the enum
      const lines = enumContent.split('\n');
      let lastNonEmptyLine = '';

      // Find the last non-empty line
      for (let i = lines.length - 1; i >= 0; i--) {
        if (lines[i].trim()) {
          lastNonEmptyLine = lines[i];
          break;
        }
      }

      // Check if the last line ends with a comma
      const hasComma = lastNonEmptyLine.trim().endsWith(',');

      if (!hasComma) {
        // Add comma to the last entry
        console.log("Adding comma to last enum entry");

        // Replace the last non-empty line with the same line + comma
        const lastLineIndex = lines.findIndex(line => line === lastNonEmptyLine);
        if (lastLineIndex !== -1) {
          lines[lastLineIndex] = lastNonEmptyLine + ',';
        }

        // Add the new entry and join the lines back together
        const newEnumContent = lines.join('\n') + `\n  ${enumName} = "${toolName}"`;
        const enumReplacement = `${newEnumContent}\n$2`;
        updatedContent = updatedContent.replace(enumRegex, enumReplacement);
      } else {
        // Just add the new entry (last entry already has a comma)
        console.log("Last enum entry already has comma");
        const enumReplacement = `$1\n  ${enumName} = "${toolName}"\n$2`;
        updatedContent = updatedContent.replace(enumRegex, enumReplacement);
      }
    } else {
      // No entries yet or couldn't find the last one
      console.log("No entries found in enum or couldn't parse last entry");
      const enumReplacement = `$1\n  ${enumName} = "${toolName}"\n$2`;
      updatedContent = updatedContent.replace(enumRegex, enumReplacement);
    }
  }

  // Add parameter interface
  const interfaceRegex = /(export type FrontendToolParams =)/;
  const interfaceReplacement = `${parameterInterface}\n\n$1`;
  updatedContent = updatedContent.replace(interfaceRegex, interfaceReplacement);

  // Add schema function
  const schemaFunctionRegex = /(export function getAllFrontendToolSchemas)/;
  const schemaFunctionReplacement = `${schemaFunction}\n\n$1`;
  updatedContent = updatedContent.replace(schemaFunctionRegex, schemaFunctionReplacement);

  // Update getAllFrontendToolSchemas function
  updatedContent = updateGetAllFunction(updatedContent, enumName);

  // Write updated content to file
  fs.writeFileSync(tsFilePath, updatedContent, 'utf8');
  console.log(`\nSuccessfully added tool "${toolName}" to frontend_tools.ts`);

  // Generate Python file
  console.log('\nGenerating Python file...');
  try {
    execSync(`node ${pyGeneratorPath}`, { stdio: 'inherit' });
    console.log('Python file generated successfully!');
  } catch (error) {
    console.error('Error generating Python file:', error);
  }
}

// Main function to update an existing tool
async function updateExistingTool() {
  console.log('\n=== Update Existing Frontend Tool ===\n');

  // Parse existing file
  const { toolNames } = parseTypeScriptFile();

  if (toolNames.length === 0) {
    console.log('No existing tools found. Please add a new tool instead.');
    return;
  }

  // Select tool to update
  const toolOptions = toolNames.map(tool => `${tool.enumName} (${tool.value})`);
  const selectedTool = await askSelection('Select a tool to update:', toolOptions);
  const toolIndex = toolOptions.indexOf(selectedTool);
  const { enumName, value: toolName } = toolNames[toolIndex];

  console.log(`\nUpdating tool: ${enumName} (${toolName})`);

  // TODO: Implement tool update logic
  console.log('\nTool update functionality is not yet implemented.');
  console.log('For now, please add a new tool and then manually remove the old one from the file.');
}

// Main function
async function main() {
  console.log('=== Frontend Tool Schema Wizard ===');
  console.log('This wizard will help you create or update frontend tool schemas.\n');

  const action = await askSelection('What would you like to do?', [
    'Add a new frontend tool',
    'Update an existing frontend tool',
    'Exit'
  ]);

  if (action === 'Add a new frontend tool') {
    await addNewTool();
  } else if (action === 'Update an existing frontend tool') {
    await updateExistingTool();
  } else {
    console.log('Exiting wizard.');
  }

  rl.close();
}

// Run the main function
main().catch(error => {
  console.error('An error occurred:', error);
  rl.close();
});
