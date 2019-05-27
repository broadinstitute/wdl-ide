import { createReadStream } from 'fs';
import { post } from 'request-promise-native';

export const submitWorkflow = (
  baseUri: string,
  wdlPath: string,
  inputsPath: string,
  optionsPath: string,
) => {
  return post(baseUri, {
    json: true,
    formData: {
      workflowSource: createReadStream(wdlPath),
      workflowInputs: createReadStream(inputsPath),
      workflowOptions: createReadStream(optionsPath),
    },
  });
};
