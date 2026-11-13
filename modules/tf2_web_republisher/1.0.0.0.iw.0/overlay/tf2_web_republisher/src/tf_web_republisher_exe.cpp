#include "tf2_web_republisher/tf2_web_republisher.hpp"

int main(int argc, char* argv[]) {
  rclcpp::init(argc, argv);
  auto node = std::make_shared<tf2_web_republisher::TFRepublisher>(rclcpp::NodeOptions());
  rclcpp::executors::SingleThreadedExecutor executor;
  executor.add_node(node);
  executor.spin();
  rclcpp::shutdown();
  return 0;
}
