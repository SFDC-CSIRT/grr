#!/usr/bin/env python
"""This modules contains tests for config API handler."""


from grr import config
from grr.lib import flags

from grr.lib import utils
from grr.server.grr_response_server import maintenance_utils
from grr.server.grr_response_server.gui import api_test_lib
from grr.server.grr_response_server.gui.api_plugins import config as config_plugin
from grr.test_lib import test_lib


def GetConfigMockClass(sections=None):
  """Mocks a configuration file for use by the API handler.

  Args:
    sections: A dict containing one key per config section
    with a value of a dict containing one key per config parameter name
    and a value of config parameter value. (default {})

  Returns:
    A class to be used as a config mock.
  """

  if sections is None:
    sections = {}

  missing = object()

  type_infos = []
  values = {}
  raw_values = {}
  default_values = {}

  for section_name, section in sections.iteritems():
    for parameter_name, parameter_data in section.iteritems():
      name = "%s.%s" % (section_name, parameter_name)
      descriptor = utils.DataObject(section=section_name, name=name)
      type_infos.append(descriptor)

      if "value" in parameter_data:
        values[name] = parameter_data["value"]

      if "raw_value" in parameter_data:
        raw_values[name] = parameter_data["raw_value"]

      if "default_value" in parameter_data:
        default_values[name] = parameter_data["default_value"]

  def Get(parameter, default=missing):
    try:
      return values[parameter]
    except KeyError:
      if default is missing:
        return default_values[parameter]
      return default

  def GetRaw(parameter, default=missing):
    try:
      return raw_values[parameter]
    except KeyError:
      if default is missing:
        return default_values[parameter]
      return default

  return {"Get": Get, "GetRaw": GetRaw, "type_infos": type_infos}


class ApiGetConfigHandlerTest(api_test_lib.ApiCallHandlerTest):
  """Test for ApiGetConfigHandlerTest."""

  def setUp(self):
    super(ApiGetConfigHandlerTest, self).setUp()
    self.handler = config_plugin.ApiGetConfigHandler()

  def _ConfigStub(self, sections=None):
    mock = GetConfigMockClass(sections)
    return utils.MultiStubber((config.CONFIG, "GetRaw", mock["GetRaw"]),
                              (config.CONFIG, "Get", mock["Get"]),
                              (config.CONFIG, "type_infos", mock["type_infos"]))

  def _HandleConfig(self, sections):
    with self._ConfigStub(sections):
      mock_request = utils.DataObject()
      result = self.handler.Handle(mock_request)

    return result

  def _assertHandlesConfig(self, sections, expected_result):
    actual_result = self._HandleConfig(sections)
    self.assertEquals(actual_result, expected_result)

  def testHandlesEmptyConfig(self):
    self._assertHandlesConfig(None, config_plugin.ApiGetConfigResult())

  def testHandlesEmptySection(self):
    self._assertHandlesConfig({
        "section": {}
    }, config_plugin.ApiGetConfigResult())

  def testHandlesConfigOption(self):
    input_dict = {
        "section": {
            "parameter": {
                "value": u"value",
                "raw_value": u"value"
            }
        }
    }
    result = self._HandleConfig(input_dict)
    self.assertEqual(len(result.sections), 1)
    self.assertEqual(len(result.sections[0].options), 1)
    self.assertEqual(result.sections[0].options[0].name, "section.parameter")
    self.assertEqual(result.sections[0].options[0].value, "value")

  def testRendersRedacted(self):
    input_dict = {
        "Mysql": {
            "database_password": {
                "value": u"secret",
                "raw_value": u"secret"
            }
        }
    }
    result = self._HandleConfig(input_dict)
    self.assertTrue(result.sections[0].options[0].is_redacted)


class ApiGetConfigOptionHandlerTest(api_test_lib.ApiCallHandlerTest):
  """Test for ApiGetConfigOptionHandler."""

  def setUp(self):
    super(ApiGetConfigOptionHandlerTest, self).setUp()
    self.handler = config_plugin.ApiGetConfigOptionHandler()

  def _ConfigStub(self, sections=None):
    mock = GetConfigMockClass(sections)
    return utils.MultiStubber((config.CONFIG, "GetRaw", mock["GetRaw"]),
                              (config.CONFIG, "Get", mock["Get"]),
                              (config.CONFIG, "type_infos", mock["type_infos"]))

  def _HandleConfigOption(self, stub_sections, name):
    with self._ConfigStub(stub_sections):
      result = self.handler.Handle(
          config_plugin.ApiGetConfigOptionArgs(name=name))

    return result

  def testRendersRedacted(self):
    input_dict = {
        "Mysql": {
            "database_password": {
                "value": u"secret",
                "raw_value": u"secret"
            }
        }
    }
    result = self._HandleConfigOption(input_dict, "Mysql.database_password")
    self.assertEqual(result.name, "Mysql.database_password")
    self.assertTrue(result.is_redacted)


class ApiGrrBinaryTestMixin(object):
  """Mixing providing GRR binaries test setup routine."""

  def SetUpBinaries(self):
    with test_lib.FakeTime(42):
      code = "I am a binary file"
      upload_path = config.CONFIG.Get("Config.aff4_root").Add(
          "executables/windows/test.exe")
      maintenance_utils.UploadSignedConfigBlob(
          code, aff4_path=upload_path, token=self.token)

    with test_lib.FakeTime(43):
      code = "I'm a python hack"
      upload_path = config.CONFIG.Get("Config.python_hack_root").Add("test")
      maintenance_utils.UploadSignedConfigBlob(
          code, aff4_path=upload_path, token=self.token)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
