#include <memory>

#include <rclcpp/executors.hpp>
#include <rclcpp/utilities.hpp>

#include "kinematic_icp_ros/nodes/online_node.hpp"

int main(int argc, char **argv) {
    rclcpp::init(argc, argv);

    auto online_node = std::make_shared<kinematic_icp_ros::OnlineNode>(rclcpp::NodeOptions());

    rclcpp::executors::SingleThreadedExecutor executor;
    executor.add_node(online_node->get_node_base_interface());
    executor.spin();

    rclcpp::shutdown();
    return 0;
}
